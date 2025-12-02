import os
from typing import Any, Dict

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

REGISTRY_BASE_URL = os.getenv("REGISTRY_BASE_URL", "http://localhost:8001")

app = FastAPI(title="Tool Gateway Service")


class ToolCallRequest(BaseModel):
    slug: str
    input: Dict[str, Any]


@app.post("/call_tool")
async def call_tool(req: ToolCallRequest):
    """
    1. Resolve tool + active version from registry.
    2. Call the underlying endpoint (currently HTTP only).
    3. Return combined response.
    """

    # 1. Resolve tool + version
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{REGISTRY_BASE_URL}/resolve", params={"slug": req.slug})
        if r.status_code != 200:
            raise HTTPException(
                status_code=r.status_code,
                detail=f"Failed to resolve tool: {r.text}",
            )
        resolved = r.json()

    version = resolved.get("version") or {}
    endpoint_url = version.get("endpoint_url")
    endpoint_method = (version.get("endpoint_method") or "POST").upper()
    protocol = version.get("endpoint_protocol", "http")

    if not endpoint_url:
        raise HTTPException(status_code=500, detail="Tool endpoint_url is not set")

    if not endpoint_url.startswith("http"):
        endpoint_url = f"{protocol}://{endpoint_url}"

    # 2. Call the underlying endpoint
    try:
        async with httpx.AsyncClient() as client:
            if endpoint_method == "GET":
                tool_resp = await client.get(endpoint_url, params=req.input)
            elif endpoint_method == "POST":
                tool_resp = await client.post(endpoint_url, json=req.input)
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unsupported endpoint_method: {endpoint_method}",
                )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error calling tool endpoint: {e}",
        )

    # Attempt to parse JSON; if it fails, return text
    try:
        tool_data = tool_resp.json()
    except ValueError:
        tool_data = {"raw": tool_resp.text}

    return {
        "tool": resolved.get("tool"),
        "version": version,
        "tool_status_code": tool_resp.status_code,
        "result": tool_data,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "registry_base_url": REGISTRY_BASE_URL}
