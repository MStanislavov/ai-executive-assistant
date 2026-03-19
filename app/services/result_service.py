"""Result query business logic for all 6 entity types."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


async def list_jobs(
    db: AsyncSession, profile_id: str, run_id: str | None = None
) -> list[JobOpportunityRead]:
    stmt = (
        select(JobOpportunity)
        .where(JobOpportunity.profile_id == profile_id)
    )
    if run_id is not None:
        stmt = stmt.where(JobOpportunity.run_id == run_id)
    stmt = stmt.order_by(JobOpportunity.created_at.desc())
    result = await db.execute(stmt)
    return [
        JobOpportunityRead(
            id=r.id, profile_id=r.profile_id, run_id=r.run_id,
            title=r.title, company=r.company, url=r.url,
            description=r.description, location=r.location,
            salary_range=r.salary_range, source_query=r.source_query,
            created_at=r.created_at,
        )
        for r in result.scalars().all()
    ]


async def list_certifications(
    db: AsyncSession, profile_id: str, run_id: str | None = None
) -> list[CertificationRead]:
    stmt = (
        select(Certification)
        .where(Certification.profile_id == profile_id)
    )
    if run_id is not None:
        stmt = stmt.where(Certification.run_id == run_id)
    stmt = stmt.order_by(Certification.created_at.desc())
    result = await db.execute(stmt)
    return [
        CertificationRead(
            id=r.id, profile_id=r.profile_id, run_id=r.run_id,
            title=r.title, provider=r.provider, url=r.url,
            description=r.description, cost=r.cost, duration=r.duration,
            created_at=r.created_at,
        )
        for r in result.scalars().all()
    ]


async def list_courses(
    db: AsyncSession, profile_id: str, run_id: str | None = None
) -> list[CourseRead]:
    stmt = (
        select(Course)
        .where(Course.profile_id == profile_id)
    )
    if run_id is not None:
        stmt = stmt.where(Course.run_id == run_id)
    stmt = stmt.order_by(Course.created_at.desc())
    result = await db.execute(stmt)
    return [
        CourseRead(
            id=r.id, profile_id=r.profile_id, run_id=r.run_id,
            title=r.title, platform=r.platform, url=r.url,
            description=r.description, cost=r.cost, duration=r.duration,
            created_at=r.created_at,
        )
        for r in result.scalars().all()
    ]


async def list_events(
    db: AsyncSession, profile_id: str, run_id: str | None = None
) -> list[EventRead]:
    stmt = (
        select(Event)
        .where(Event.profile_id == profile_id)
    )
    if run_id is not None:
        stmt = stmt.where(Event.run_id == run_id)
    stmt = stmt.order_by(Event.created_at.desc())
    result = await db.execute(stmt)
    return [
        EventRead(
            id=r.id, profile_id=r.profile_id, run_id=r.run_id,
            title=r.title, organizer=r.organizer, url=r.url,
            description=r.description, event_date=r.event_date,
            location=r.location, created_at=r.created_at,
        )
        for r in result.scalars().all()
    ]


async def list_groups(
    db: AsyncSession, profile_id: str, run_id: str | None = None
) -> list[GroupRead]:
    stmt = (
        select(Group)
        .where(Group.profile_id == profile_id)
    )
    if run_id is not None:
        stmt = stmt.where(Group.run_id == run_id)
    stmt = stmt.order_by(Group.created_at.desc())
    result = await db.execute(stmt)
    return [
        GroupRead(
            id=r.id, profile_id=r.profile_id, run_id=r.run_id,
            title=r.title, platform=r.platform, url=r.url,
            description=r.description, member_count=r.member_count,
            created_at=r.created_at,
        )
        for r in result.scalars().all()
    ]


async def list_trends(
    db: AsyncSession, profile_id: str, run_id: str | None = None
) -> list[TrendRead]:
    stmt = (
        select(Trend)
        .where(Trend.profile_id == profile_id)
    )
    if run_id is not None:
        stmt = stmt.where(Trend.run_id == run_id)
    stmt = stmt.order_by(Trend.created_at.desc())
    result = await db.execute(stmt)
    return [
        TrendRead(
            id=r.id, profile_id=r.profile_id, run_id=r.run_id,
            title=r.title, category=r.category, url=r.url,
            description=r.description, relevance=r.relevance,
            source=r.source, created_at=r.created_at,
        )
        for r in result.scalars().all()
    ]


# --- Generic update / delete helpers ---


async def _get_by_id(db: AsyncSession, model_cls, profile_id: str, item_id: str):
    result = await db.execute(
        select(model_cls).where(
            model_cls.id == item_id, model_cls.profile_id == profile_id
        )
    )
    return result.scalar_one_or_none()


async def update_result_title(
    db: AsyncSession, model_cls, profile_id: str, item_id: str, title: str
):
    item = await _get_by_id(db, model_cls, profile_id, item_id)
    if item is None:
        return None
    item.title = title
    await db.commit()
    await db.refresh(item)
    return item


async def delete_result(
    db: AsyncSession, model_cls, profile_id: str, item_id: str
) -> bool:
    item = await _get_by_id(db, model_cls, profile_id, item_id)
    if item is None:
        return False
    await db.delete(item)
    await db.commit()
    return True
