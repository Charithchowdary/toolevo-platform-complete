from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .models import ToolStatus


class ToolBase(BaseModel):
    slug: str
    display_name: str
    description: Optional[str] = None


class ToolCreate(ToolBase):
    pass


class ToolRead(ToolBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ToolVersionBase(BaseModel):
    version: str
    status: ToolStatus = ToolStatus.draft
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

    endpoint_protocol: str
    endpoint_method: Optional[str] = None
    endpoint_url: Optional[str] = None

    auth_type: str = "none"
    auth_key_name: Optional[str] = None
    auth_key_location: Optional[str] = None

    cost_per_call_usd: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None


class ToolVersionCreate(ToolVersionBase):
    pass


class ToolVersionRead(ToolVersionBase):
    id: str
    tool_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ToolWithVersions(ToolRead):
    versions: List[ToolVersionRead] = []


class StatusUpdate(BaseModel):
    status: ToolStatus
