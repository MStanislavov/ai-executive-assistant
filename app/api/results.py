"""Results HTTP endpoints: list, update, and delete results for all 6 entity types."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.certification import Certification
from app.models.course import Course
from app.models.event import Event
from app.models.group import Group
from app.models.job_opportunity import JobOpportunity
from app.models.trend import Trend
from app.schemas.certification import CertificationRead
from app.schemas.course import CourseRead
from app.schemas.event import EventRead
from app.schemas.group import GroupRead
from app.schemas.job_opportunity import JobOpportunityRead
from app.schemas.trend import TrendRead
from app.services import result_service

router = APIRouter(tags=["results"])


class ResultTitleUpdate(BaseModel):
    title: str


# --- List endpoints ---


@router.get("/profiles/{profile_id}/results/jobs")
async def list_jobs(
    profile_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    run_id: str | None = None,
) -> list[JobOpportunityRead]:
    return await result_service.list_jobs(db, profile_id, run_id)


@router.get("/profiles/{profile_id}/results/certifications")
async def list_certifications(
    profile_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    run_id: str | None = None,
) -> list[CertificationRead]:
    return await result_service.list_certifications(db, profile_id, run_id)


@router.get("/profiles/{profile_id}/results/courses")
async def list_courses(
    profile_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    run_id: str | None = None,
) -> list[CourseRead]:
    return await result_service.list_courses(db, profile_id, run_id)


@router.get("/profiles/{profile_id}/results/events")
async def list_events(
    profile_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    run_id: str | None = None,
) -> list[EventRead]:
    return await result_service.list_events(db, profile_id, run_id)


@router.get("/profiles/{profile_id}/results/groups")
async def list_groups(
    profile_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    run_id: str | None = None,
) -> list[GroupRead]:
    return await result_service.list_groups(db, profile_id, run_id)


@router.get("/profiles/{profile_id}/results/trends")
async def list_trends(
    profile_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    run_id: str | None = None,
) -> list[TrendRead]:
    return await result_service.list_trends(db, profile_id, run_id)


# --- PATCH endpoints (rename title) ---


@router.patch("/profiles/{profile_id}/results/jobs/{item_id}")
async def update_job(
    profile_id: str,
    item_id: str,
    body: ResultTitleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobOpportunityRead:
    item = await result_service.update_result_title(
        db, JobOpportunity, profile_id, item_id, body.title
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return JobOpportunityRead.model_validate(item)


@router.patch("/profiles/{profile_id}/results/certifications/{item_id}")
async def update_certification(
    profile_id: str,
    item_id: str,
    body: ResultTitleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CertificationRead:
    item = await result_service.update_result_title(
        db, Certification, profile_id, item_id, body.title
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return CertificationRead.model_validate(item)


@router.patch("/profiles/{profile_id}/results/courses/{item_id}")
async def update_course(
    profile_id: str,
    item_id: str,
    body: ResultTitleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CourseRead:
    item = await result_service.update_result_title(
        db, Course, profile_id, item_id, body.title
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return CourseRead.model_validate(item)


@router.patch("/profiles/{profile_id}/results/events/{item_id}")
async def update_event(
    profile_id: str,
    item_id: str,
    body: ResultTitleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventRead:
    item = await result_service.update_result_title(
        db, Event, profile_id, item_id, body.title
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return EventRead.model_validate(item)


@router.patch("/profiles/{profile_id}/results/groups/{item_id}")
async def update_group(
    profile_id: str,
    item_id: str,
    body: ResultTitleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GroupRead:
    item = await result_service.update_result_title(
        db, Group, profile_id, item_id, body.title
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return GroupRead.model_validate(item)


@router.patch("/profiles/{profile_id}/results/trends/{item_id}")
async def update_trend(
    profile_id: str,
    item_id: str,
    body: ResultTitleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrendRead:
    item = await result_service.update_result_title(
        db, Trend, profile_id, item_id, body.title
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return TrendRead.model_validate(item)


# --- DELETE endpoints ---


@router.delete("/profiles/{profile_id}/results/jobs/{item_id}")
async def delete_job(
    profile_id: str,
    item_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    if not await result_service.delete_result(db, JobOpportunity, profile_id, item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"detail": "Deleted"}


@router.delete("/profiles/{profile_id}/results/certifications/{item_id}")
async def delete_certification(
    profile_id: str,
    item_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    if not await result_service.delete_result(
        db, Certification, profile_id, item_id
    ):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"detail": "Deleted"}


@router.delete("/profiles/{profile_id}/results/courses/{item_id}")
async def delete_course(
    profile_id: str,
    item_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    if not await result_service.delete_result(db, Course, profile_id, item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"detail": "Deleted"}


@router.delete("/profiles/{profile_id}/results/events/{item_id}")
async def delete_event(
    profile_id: str,
    item_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    if not await result_service.delete_result(db, Event, profile_id, item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"detail": "Deleted"}


@router.delete("/profiles/{profile_id}/results/groups/{item_id}")
async def delete_group(
    profile_id: str,
    item_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    if not await result_service.delete_result(db, Group, profile_id, item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"detail": "Deleted"}


@router.delete("/profiles/{profile_id}/results/trends/{item_id}")
async def delete_trend(
    profile_id: str,
    item_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    if not await result_service.delete_result(db, Trend, profile_id, item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"detail": "Deleted"}
