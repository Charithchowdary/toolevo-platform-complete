import os
from enum import Enum
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

REGISTRY_BASE_URL = os.getenv("REGISTRY_BASE_URL", "http://localhost:8001")

app = FastAPI(title="Variability Engine (Stub)")


class MutationType(str, Enum):
    RENAME_PARAM = "RENAME_PARAM"
    ADD_PARAM = "ADD_PARAM"
    REMOVE_PARAM = "REMOVE_PARAM"
    ADD_FIELD_TO_RESPONSE = "ADD_FIELD_TO_RESPONSE"
    REMOVE_FIELD_FROM_RESPONSE = "REMOVE_FIELD_FROM_RESPONSE"
    DEPRECATE_VERSION = "DEPRECATE_VERSION"
    CREATE_NEW_VERSION = "CREATE_NEW_VERSION"


class Mutation(BaseModel):
    type: MutationType
    toolId: str
    toolVersionId: Optional[str] = None
    payload: Dict[str, Any]
    mode: str = "dry-run"  # or "commit"


class ApplyMutationResponse(BaseModel):
    mutation: Mutation
    note: str
    currentVersion: Optional[Dict[str, Any]] = None
    newVersionPreview: Optional[Dict[str, Any]] = None


@app.post("/mutations/apply", response_model=ApplyMutationResponse)
async def apply_mutation(mutation: Mutation):
    """
    Very lightweight stub:

    - Fetches the current ToolVersion from the registry (if toolVersionId provided)
    - Does NOT actually persist any change yet; just echoes a preview.
    - You can extend this to modify schemas and POST/PATCH back to the registry.
    """

    current_version = None

    if mutation.toolVersionId:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{REGISTRY_BASE_URL}/tools/{mutation.toolId}/versions/{mutation.toolVersionId}"
            )
            if r.status_code == 200:
                current_version = r.json()

    note = (
        "dry-run only; no change applied. Extend this service to write back to registry."
        if mutation.mode == "dry-run"
        else "commit mode requested, but this stub only previews changes."
    )

    # For now, we just attach the payload as a fake 'newVersionPreview'
    new_version_preview = None
    if current_version is not None:
        new_version_preview = {**current_version, "mutationPayload": mutation.payload}

    return ApplyMutationResponse(
        mutation=mutation,
        note=note,
        currentVersion=current_version,
        newVersionPreview=new_version_preview,
    )


@app.get("/health")
async def health():
    return {"status": "ok", "registry_base_url": REGISTRY_BASE_URL}
