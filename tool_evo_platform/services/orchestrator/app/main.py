import json
import os
from typing import Any, Dict, List

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

GATEWAY_BASE_URL = os.getenv("GATEWAY_BASE_URL", "http://localhost:8003")
REGISTRY_BASE_URL = os.getenv("REGISTRY_BASE_URL", "http://localhost:8001")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Optional LLM client for NL endpoints
try:
    from openai import OpenAI

    llm_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
except ImportError:
    llm_client = None

app = FastAPI(title="Orchestrator Service (LLM + Tool Router)")


class ExecuteRequest(BaseModel):
    slug: str
    input: Dict[str, Any]


class NLExecuteRequest(BaseModel):
    slug: str = Field(..., description="Tool slug, e.g. 'weather-service'")
    query: str = Field(..., description="User natural language instruction")


class NLRouteRequest(BaseModel):
    query: str = Field(..., description="User natural language instruction")


class ToolSummary(BaseModel):
    slug: str
    display_name: str
    description: str | None = None


def require_llm():
    if llm_client is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "LLM client not configured. "
                "Install `openai` and set OPENAI_API_KEY env var in orchestrator to use NL endpoints."
            ),
        )


@app.post("/execute")
async def execute(req: ExecuteRequest):
    """
    Simple orchestrator:

    - For explicit tool calls: you already know the slug + args.
    - Just forwards to the gateway.
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{GATEWAY_BASE_URL}/call_tool",
            json={"slug": req.slug, "input": req.input},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {
        "orchestrator": "ok",
        "mode": "direct",
        "gateway_response": r.json(),
    }


@app.post("/nl_execute")
async def nl_execute(req: NLExecuteRequest):
    """
    Natural-language orchestrator for a *specific* tool:

    1. Use an LLM to convert the user query into a JSON object matching the tool input.
    2. Send that JSON as `input` to the gateway.
    """
    require_llm()

    system_prompt = (
        "You are a tool argument builder. "
        "Given a user request and a tool slug, you MUST output ONLY a JSON object "
        "for the tool input parameters, with no explanation or extra text."
    )
    user_prompt = (
        f"Tool slug: {req.slug}\n"
        f"User request: {req.query}\n"
        "Output a JSON object with the correct fields and values for this tool's input."
    )

    try:
        completion = llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content
        tool_args = json.loads(content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calling LLM or parsing its response: {e}",
        )

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{GATEWAY_BASE_URL}/call_tool",
            json={"slug": req.slug, "input": tool_args},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return {
        "orchestrator": "ok",
        "mode": "llm-single-tool",
        "tool_input": tool_args,
        "gateway_response": r.json(),
    }


@app.post("/nl_route")
async def nl_route(req: NLRouteRequest):
    """
    Full LLM router:

    1. Fetch list of available tools from the registry.
    2. Ask an LLM to:
       - choose the best tool slug (or none),
       - build JSON arguments for it.
    3. If a tool is chosen, call the gateway and return the result.
    """
    require_llm()

    # 1. Fetch tools from registry
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{REGISTRY_BASE_URL}/tools")
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tools from registry: {r.text}")

    tools_raw = r.json()
    tools: List[ToolSummary] = [
        ToolSummary(
            slug=t["slug"],
            display_name=t.get("display_name", t["slug"]),
            description=t.get("description"),
        )
        for t in tools_raw
    ]

    tools_json = json.dumps([t.dict() for t in tools], ensure_ascii=False)

    system_prompt = (
        "You are a routing controller for tools.\n"
        "You are given a list of tools (with slug, name, description) and a user request.\n"
        "Your job is to:\n"
        "1) Decide which single tool (if any) is best suited to handle the request.\n"
        "2) Construct a JSON object with arguments for that tool.\n\n"
        "Return ONLY a JSON object with the following keys:\n"
        "{\n"
        "  \"slug\": string | null,  // chosen tool slug or null if none fits\n"
        "  \"args\": object          // JSON args to send to this tool ({} if slug is null)\n"
        "}\n"
        "Do not include any explanation, only valid JSON."
    )

    user_prompt = (
        f"Available tools (JSON list):\n{tools_json}\n\n"
        f"User request: {req.query}\n\n"
        "Pick the most appropriate tool (or null) and arguments."
    )

    try:
        completion = llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content
        parsed = json.loads(content)
        chosen_slug = parsed.get("slug")
        args = parsed.get("args", {})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calling LLM or parsing router response: {e}",
        )

    if not chosen_slug:
        # LLM decided none of the tools fit; just return its reasoning (args) if any.
        return {
            "orchestrator": "ok",
            "mode": "llm-router-no-tool",
            "available_tools": [t.dict() for t in tools],
            "router_output": {
                "slug": None,
                "args": args,
            },
        }

    # 3. Call the gateway with the chosen slug + args
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{GATEWAY_BASE_URL}/call_tool",
            json={"slug": chosen_slug, "input": args},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return {
        "orchestrator": "ok",
        "mode": "llm-router",
        "chosen_tool": chosen_slug,
        "tool_input": args,
        "gateway_response": r.json(),
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "gateway_base_url": GATEWAY_BASE_URL,
        "registry_base_url": REGISTRY_BASE_URL,
        "llm_enabled": llm_client is not None,
    }
