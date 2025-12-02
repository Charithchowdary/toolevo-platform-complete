from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from . import models, schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tool Registry Service")


@app.post("/tools", response_model=schemas.ToolRead, status_code=201)
def create_tool(tool: schemas.ToolCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(models.Tool)
        .filter(models.Tool.slug == tool.slug)
        .one_or_none()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Tool with this slug already exists")
    db_tool = models.Tool(
        slug=tool.slug,
        display_name=tool.display_name,
        description=tool.description,
    )
    db.add(db_tool)
    db.commit()
    db.refresh(db_tool)
    return db_tool


@app.get("/tools", response_model=List[schemas.ToolRead])
def list_tools(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by slug or display_name"),
):
    q = db.query(models.Tool)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (models.Tool.slug.ilike(like))
            | (models.Tool.display_name.ilike(like))
        )
    return q.order_by(models.Tool.created_at.desc()).all()


@app.get("/tools/{tool_id}", response_model=schemas.ToolWithVersions)
def get_tool(tool_id: str, db: Session = Depends(get_db)):
    tool = (
        db.query(models.Tool)
        .filter(models.Tool.id == tool_id)
        .one_or_none()
    )
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


@app.post(
    "/tools/{tool_id}/versions",
    response_model=schemas.ToolVersionRead,
    status_code=201,
)
def create_tool_version(
    tool_id: str,
    payload: schemas.ToolVersionCreate,
    db: Session = Depends(get_db),
):
    tool = (
        db.query(models.Tool)
        .filter(models.Tool.id == tool_id)
        .one_or_none()
    )
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    db_version = models.ToolVersion(
        tool_id=tool.id,
        version=payload.version,
        status=payload.status,
        input_schema=payload.input_schema,
        output_schema=payload.output_schema,
        endpoint_protocol=payload.endpoint_protocol,
        endpoint_method=payload.endpoint_method,
        endpoint_url=payload.endpoint_url,
        auth_type=payload.auth_type,
        auth_key_name=payload.auth_key_name,
        auth_key_location=payload.auth_key_location,
        cost_per_call_usd=payload.cost_per_call_usd,
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
    )
    db.add(db_version)
    db.commit()
    db.refresh(db_version)
    return db_version


@app.get(
    "/tools/{tool_id}/versions",
    response_model=List[schemas.ToolVersionRead],
)
def list_tool_versions(
    tool_id: str,
    status: Optional[models.ToolStatus] = Query(
        None, description="Filter by status"
    ),
    db: Session = Depends(get_db),
):
    q = db.query(models.ToolVersion).filter(models.ToolVersion.tool_id == tool_id)
    if status:
        q = q.filter(models.ToolVersion.status == status)
    return q.order_by(models.ToolVersion.created_at.desc()).all()


@app.get(
    "/tools/{tool_id}/versions/{version_id}",
    response_model=schemas.ToolVersionRead,
)
def get_tool_version(
    tool_id: str,
    version_id: str,
    db: Session = Depends(get_db),
):
    version = (
        db.query(models.ToolVersion)
        .filter(
            models.ToolVersion.tool_id == tool_id,
            models.ToolVersion.id == version_id,
        )
        .one_or_none()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Tool version not found")
    return version


@app.patch(
    "/tools/{tool_id}/versions/{version_id}/status",
    response_model=schemas.ToolVersionRead,
)
def update_tool_version_status(
    tool_id: str,
    version_id: str,
    status_update: schemas.StatusUpdate,
    db: Session = Depends(get_db),
):
    version = (
        db.query(models.ToolVersion)
        .filter(
            models.ToolVersion.tool_id == tool_id,
            models.ToolVersion.id == version_id,
        )
        .one_or_none()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Tool version not found")

    version.status = status_update.status
    version.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(version)
    return version


@app.get("/resolve")
def resolve_tool(
    slug: str = Query(..., description="Tool slug"),
    db: Session = Depends(get_db),
):
    tool = (
        db.query(models.Tool)
        .filter(models.Tool.slug == slug)
        .one_or_none()
    )
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Choose the latest active version by created_at
    version = (
        db.query(models.ToolVersion)
        .filter(
            models.ToolVersion.tool_id == tool.id,
            models.ToolVersion.status == models.ToolStatus.active,
        )
        .order_by(models.ToolVersion.created_at.desc())
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="No active version for this tool")

    return {
        "tool": schemas.ToolRead.from_orm(tool),
        "version": schemas.ToolVersionRead.from_orm(version),
    }
