# =============================================================================
# models/template.py
# =============================================================================
# Pydantic schemas + enums for the Sprint 5 "Clone-from-Template" feature.
#
# A teacher publishes a golden VM as a template, groups students into a class,
# then bulk-clones the template to every student in that class. The cloned VMs
# themselves live in vm_jobs; these schemas cover the template/class/clone
# lineage layered on top.
#
# See docs/design/clone-templates-architecture.md
# =============================================================================

import re
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CloneMode(str, Enum):
    """How a template is cloned for each student."""
    full = "full"       # independent disk copy — slower, more storage
    linked = "linked"   # shares the template's base disk — near-instant, tiny


class TemplateStatus(str, Enum):
    draft = "draft"          # created, not yet distributable
    published = "published"  # frozen (for linked) and ready to distribute
    archived = "archived"    # retired — hidden, no new distributions


# ---------------------------------------------------------------------------
# Shared validators
# ---------------------------------------------------------------------------

def _validate_name(v: str) -> str:
    """Names: 3-40 chars, letters/digits/space/hyphen/underscore."""
    if not re.match(r'^[A-Za-z0-9 _\-]{3,40}$', v):
        raise ValueError(
            "name must be 3-40 characters: letters, digits, spaces, - or _."
        )
    return v


# ---------------------------------------------------------------------------
# Template schemas
# ---------------------------------------------------------------------------

class TemplateCreateRequest(BaseModel):
    """
    Publish a template from an existing VM job. The teacher points at one of
    their VMs (by vm_job_id) which becomes the golden source.
    """
    name: str
    vm_job_id: int                       # source VM the teacher already built
    description: Optional[str] = None
    clone_mode: CloneMode = CloneMode.full
    default_cpu: int = Field(default=2, ge=1, le=16)
    default_ram_mb: int = Field(default=2048, ge=512, le=65536)

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        return _validate_name(v)


class TemplateUpdateRequest(BaseModel):
    """Patch a template's metadata, specs, or lifecycle status."""
    name: Optional[str] = None
    description: Optional[str] = None
    clone_mode: Optional[CloneMode] = None
    default_cpu: Optional[int] = Field(default=None, ge=1, le=16)
    default_ram_mb: Optional[int] = Field(default=None, ge=512, le=65536)
    status: Optional[TemplateStatus] = None

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: Optional[str]) -> Optional[str]:
        return _validate_name(v) if v is not None else v


class TemplateResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    description: Optional[str] = None
    source_vmid: int
    os_choice: str
    clone_mode: str
    default_cpu: int
    default_ram_mb: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Class / enrollment schemas
# ---------------------------------------------------------------------------

class ClassCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        return _validate_name(v)


class EnrollRequest(BaseModel):
    """Enroll one or more students into a class by their user ids."""
    student_ids: List[int] = Field(min_length=1)


class StudentResponse(BaseModel):
    id: int
    username: str
    enrolled_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ClassResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    student_count: int = 0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Distribution / batch schemas
# ---------------------------------------------------------------------------

class DistributeRequest(BaseModel):
    """
    Distribute a template to every student in a class. Per-distribution
    overrides for specs and clone mode are optional — if omitted, the
    template's defaults are used.
    """
    class_id: int
    cpu_cores: Optional[int] = Field(default=None, ge=1, le=16)
    ram_mb: Optional[int] = Field(default=None, ge=512, le=65536)
    clone_mode: Optional[CloneMode] = None


class CloneJobResponse(BaseModel):
    id: int
    student_id: int
    username: Optional[str] = None
    vm_job_id: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    vm_name: Optional[str] = None
    vmid: Optional[int] = None
    vm_status: Optional[str] = None
    vm_ip: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BatchResponse(BaseModel):
    id: int
    template_id: int
    class_id: int
    initiated_by: int
    clone_mode: str
    cpu_cores: int
    ram_mb: int
    total: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BatchProgressResponse(BatchResponse):
    """A batch plus its per-student clone progress."""
    clones: List[CloneJobResponse] = []
