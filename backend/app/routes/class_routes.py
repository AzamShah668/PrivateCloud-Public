# =============================================================================
# routes/class_routes.py
# =============================================================================
# Admin-only API for managing student classes used by the Clone-from-Template
# feature. A class is a reusable group of students a teacher can distribute a
# template to.
#
# Endpoints (all require admin):
#   POST   /classes                        → create a class
#   GET    /classes                        → list classes (+ student counts)
#   GET    /classes/{id}                   → class detail + enrolled students
#   POST   /classes/{id}/students          → enroll students (by user id)
#   DELETE /classes/{id}/students/{uid}    → unenroll a student
#
# See docs/design/clone-templates-architecture.md
# =============================================================================

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import require_admin
from app.models.user import UserInDB
from app.models.template import (
    ClassCreateRequest,
    ClassResponse,
    EnrollRequest,
    StudentResponse,
)
from db import database
from db import templates as tdb

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/classes", tags=["Classes"])


class ClassDetailResponse(ClassResponse):
    students: List[StudentResponse] = []


class EnrollResultResponse(BaseModel):
    enrolled: int  # number of NEW enrollments created


@router.post("", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
def create_class(req: ClassCreateRequest, admin: UserInDB = Depends(require_admin)):
    row = tdb.create_class(owner_id=admin.id, name=req.name, description=req.description)
    row = {**row, "student_count": 0}
    database.log_action(
        user_id=admin.id, action_type="class.create",
        action="class.create", target_type="class_group",
        target_id=str(row["id"]), details={"name": req.name},
    )
    return ClassResponse.model_validate(row)


@router.get("", response_model=List[ClassResponse])
def list_classes(admin: UserInDB = Depends(require_admin)):
    return [ClassResponse.model_validate(c) for c in tdb.list_classes()]


@router.get("/{class_id}", response_model=ClassDetailResponse)
def get_class(class_id: int, admin: UserInDB = Depends(require_admin)):
    cls = tdb.get_class(class_id)
    if not cls:
        raise HTTPException(status_code=404, detail=f"Class {class_id} not found.")
    students = tdb.list_class_students(class_id)
    payload = {**cls, "student_count": len(students), "students": students}
    return ClassDetailResponse.model_validate(payload)


@router.post("/{class_id}/students", response_model=EnrollResultResponse)
def enroll_students(
    class_id: int,
    req: EnrollRequest,
    admin: UserInDB = Depends(require_admin),
):
    if not tdb.get_class(class_id):
        raise HTTPException(status_code=404, detail=f"Class {class_id} not found.")

    # Validate every id refers to a real, non-admin user before enrolling.
    # Admins are excluded so template distribution never creates VMs under an
    # admin account (confusing lineage + collides with their own VMs).
    for sid in req.student_ids:
        user = database.get_user_by_id(sid)
        if not user:
            raise HTTPException(status_code=400, detail=f"User {sid} does not exist.")
        if user.get("role") == "admin":
            raise HTTPException(
                status_code=400,
                detail=f"User '{user['username']}' is an admin and cannot be enrolled as a student.",
            )

    created = tdb.enroll_students(class_id, req.student_ids)
    database.log_action(
        user_id=admin.id, action_type="class.enroll",
        action="class.enroll", target_type="class_group",
        target_id=str(class_id),
        details={"student_ids": req.student_ids, "newly_enrolled": created},
    )
    return EnrollResultResponse(enrolled=created)


@router.delete("/{class_id}/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def unenroll_student(
    class_id: int,
    student_id: int,
    admin: UserInDB = Depends(require_admin),
):
    if not tdb.get_class(class_id):
        raise HTTPException(status_code=404, detail=f"Class {class_id} not found.")
    tdb.unenroll_student(class_id, student_id)
    database.log_action(
        user_id=admin.id, action_type="class.enroll",
        action="class.unenroll", target_type="class_group",
        target_id=str(class_id), details={"removed_student_id": student_id},
    )
    return None
