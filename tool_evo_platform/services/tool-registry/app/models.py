import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship

from .db import Base


class Tool(Base):
    __tablename__ = "tools"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    versions = relationship("ToolVersion", back_populates="tool", cascade="all, delete-orphan")


class ToolStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    deprecated = "deprecated"
    retired = "retired"


class ToolVersion(Base):
    __tablename__ = "tool_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tool_id = Column(String, ForeignKey("tools.id"), nullable=False, index=True)
    version = Column(String, nullable=False)
    status = Column(Enum(ToolStatus), default=ToolStatus.draft, nullable=False)

    input_schema = Column(JSON, nullable=False)
    output_schema = Column(JSON, nullable=False)

    endpoint_protocol = Column(String, nullable=False)  # "http", "https", "grpc", "internal"
    endpoint_method = Column(String, nullable=True)     # "GET", "POST", ...
    endpoint_url = Column(String, nullable=True)

    auth_type = Column(String, nullable=False, default="none")
    auth_key_name = Column(String, nullable=True)
    auth_key_location = Column(String, nullable=True)

    cost_per_call_usd = Column(String, nullable=True)

    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    tool = relationship("Tool", back_populates="versions")
