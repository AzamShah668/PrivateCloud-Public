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
    building = "building"    # dedicated Proxmox template is being cloned/frozen
    published = "published"  # frozen Proxmox template ready to clone/distribute
    failed = "failed"        # the build (clone → qm template) failed
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
    template_vmid: Optional[int] = None  # dedicated frozen Proxmox template VMID
    os_choice: str
    clone_mode: str
    default_cpu: int
    default_ram_mb: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeployFromTemplateRequest(BaseModel):
    """
    Deploy a single VM from a published template (admin self-serve, shown as a
    'Templates' category in the Deploy page). Specs default to the template's
    defaults; clone mode defaults to the template's clone_mode.
    """
    vm_name: str
    cpu_cores: Optional[int] = Field(default=None, ge=1, le=16)
    ram_mb: Optional[int] = Field(default=None, ge=512, le=65536)
    clone_mode: Optional[CloneMode] = None

    @field_validator("vm_name")
    @classmethod
    def vm_name_valid(cls, v: str) -> str:
        # Proxmox-safe VM name: letters/digits/hyphen, 1-30 chars (matches the
        # student-clone naming rules used elsewhere).
        if not re.match(r'^[a-zA-Z0-9-]{1,30}$', v):
            raise ValueError(
                "vm_name must be 1-30 characters: letters, digits, or hyphens."
            )
        return v


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


# ---------------------------------------------------------------------------
# Assignment schemas (student self-serve deploy)
# ---------------------------------------------------------------------------

class AssignRequest(BaseModel):
    """Assign a template to every student in a class (no VMs created)."""
    class_id: int
    cpu_cores: Optional[int] = Field(default=None, ge=1, le=16)
    ram_mb: Optional[int] = Field(default=None, ge=512, le=65536)
    clone_mode: Optional[CloneMode] = None


class StudentTemplateResponse(BaseModel):
    """What a student sees on the Deploy page: template info + assigned specs."""
    id: int                             # assignment row id
    template_id: int
    template_name: str
    description: Optional[str] = None
    os_choice: str
    cpu_cores: int
    ram_mb: int
    clone_mode: str
    status: str                         # available | deployed
    template_status: str                # published (always, for visible ones)
    template_vmid: Optional[int] = None
    assigned_at: datetime
    vm_job_id: Optional[int] = None

    model_config = {"from_attributes": True}


class AssignmentResponse(BaseModel):
    """Admin view of an individual assignment."""
    id: int
    template_id: int
    student_id: int
    username: Optional[str] = None
    class_id: Optional[int] = None
    assigned_by: int
    assigned_at: datetime
    cpu_cores: int
    ram_mb: int
    clone_mode: str
    vm_job_id: Optional[int] = None
    status: str

    model_config = {"from_attributes": True}


class AssignmentCountResponse(BaseModel):
    """Quick summary counts for a template's assignments."""
    total: int = 0
    available: int = 0
    deployed: int = 0
    revoked: int = 0

    model_config = {"from_attributes": True}

