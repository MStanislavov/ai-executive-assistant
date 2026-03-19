"""Profile business logic: CRUD, CV upload, skill extraction."""

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path

from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from pypdf import PdfReader
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.certification import Certification
from app.models.course import Course
from app.models.cover_letter import CoverLetter
from app.models.event import Event
from app.models.group import Group
from app.models.job_opportunity import JobOpportunity
from app.models.profile import UserProfile
from app.models.run import Run
from app.models.trend import Trend
from app.schemas.profile import ProfileCreate, ProfileRead, ProfileUpdate

logger = logging.getLogger(__name__)


class ExtractedSkills(BaseModel):
    skills: list[str]


def _serialize_list(value: list[str] | None) -> str | None:
    """Serialize a list to JSON string for Text column storage."""
    if value is None:
        return None
    return json.dumps(value)


def _deserialize_list(value: str | None) -> list[str] | None:
    """Deserialize a JSON string from the Text column to list."""
    if value is None:
        return None
    return json.loads(value)


def profile_to_read(profile: UserProfile) -> ProfileRead:
    """Convert an SQLAlchemy UserProfile to a ProfileRead schema."""
    return ProfileRead(
        id=profile.id,
        name=profile.name,
        targets=_deserialize_list(profile.targets),
        constraints=_deserialize_list(profile.constraints),
        skills=_deserialize_list(profile.skills),
        cv_path=profile.cv_path,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


async def create_profile(db: AsyncSession, body: ProfileCreate) -> ProfileRead:
    profile = UserProfile(
        name=body.name,
        targets=_serialize_list(body.targets),
        constraints=_serialize_list(body.constraints),
        skills=_serialize_list(body.skills),
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile_to_read(profile)


async def list_profiles(db: AsyncSession) -> list[ProfileRead]:
    result = await db.execute(select(UserProfile).order_by(UserProfile.created_at))
    profiles = result.scalars().all()
    return [profile_to_read(p) for p in profiles]


async def get_profile(db: AsyncSession, profile_id: str) -> ProfileRead | None:
    """Return ProfileRead or None if not found."""
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        return None
    return profile_to_read(profile)


async def update_profile(
    db: AsyncSession, profile_id: str, body: ProfileUpdate
) -> ProfileRead | None:
    """Return updated ProfileRead or None if not found."""
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        return None

    update_data = body.model_dump(exclude_unset=True)
    for field in ("targets", "constraints", "skills"):
        if field in update_data:
            update_data[field] = _serialize_list(update_data[field])

    for key, value in update_data.items():
        setattr(profile, key, value)

    await db.commit()
    await db.refresh(profile)
    return profile_to_read(profile)


async def delete_profile(db: AsyncSession, profile_id: str) -> bool:
    """Delete profile and cascade. Returns False if not found."""
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        return False

    # Collect run IDs for this profile
    run_rows = await db.execute(
        select(Run.id).where(Run.profile_id == profile_id)
    )
    run_ids = [r for (r,) in run_rows.all()]

    # Delete children of runs (order matters for FK constraints)
    if run_ids:
        await db.execute(delete(JobOpportunity).where(JobOpportunity.run_id.in_(run_ids)))
        await db.execute(delete(Certification).where(Certification.run_id.in_(run_ids)))
        await db.execute(delete(Course).where(Course.run_id.in_(run_ids)))
        await db.execute(delete(Event).where(Event.run_id.in_(run_ids)))
        await db.execute(delete(Group).where(Group.run_id.in_(run_ids)))
        await db.execute(delete(Trend).where(Trend.run_id.in_(run_ids)))

    # Delete profile-scoped records
    await db.execute(delete(CoverLetter).where(CoverLetter.profile_id == profile_id))
    if run_ids:
        await db.execute(delete(Run).where(Run.profile_id == profile_id))

    await db.delete(profile)
    await db.commit()

    # Clean up filesystem artifacts
    cv_dir = settings.artifacts_dir / "cvs" / profile_id
    if cv_dir.exists():
        shutil.rmtree(cv_dir)

    for run_id in run_ids:
        run_dir = settings.artifacts_dir / "runs" / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)

    return True


async def upload_cv(
    db: AsyncSession, profile_id: str, filename: str, content: bytes
) -> ProfileRead | None:
    """Save CV file and update profile. Returns None if profile not found."""
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        return None

    cv_dir = settings.artifacts_dir / "cvs" / profile_id
    os.makedirs(cv_dir, exist_ok=True)

    file_path = cv_dir / filename
    await asyncio.to_thread(Path(file_path).write_bytes, content)

    profile.cv_path = str(file_path)
    await db.commit()
    await db.refresh(profile)
    return profile_to_read(profile)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text content from a PDF file."""
    reader = PdfReader(file_path)
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n".join(text_parts)


def extract_skills_with_ai(cv_text: str) -> list[str]:
    """Use ChatOpenAI to extract skills from CV text."""
    llm = ChatOpenAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        api_key=settings.api_key,
    )
    structured_llm = llm.with_structured_output(ExtractedSkills)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a skill extraction assistant. Extract technical skills, "
                "tools, frameworks, programming languages, and professional competencies "
                "from the CV text. Return a JSON object with a single key 'skills' "
                "containing an array of skill strings. Keep each skill concise (1-3 words). "
                "Deduplicate and normalize (e.g. 'JS' -> 'JavaScript')."
            ),
        },
        {"role": "user", "content": cv_text[:8000]},
    ]
    result = structured_llm.invoke(messages)
    return result.skills


async def extract_skills_from_cv(
    db: AsyncSession, profile_id: str
) -> ExtractedSkills:
    """Extract skills from profile's CV. Raises LookupError or ValueError."""
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        raise LookupError("Profile not found")
    if not profile.cv_path:
        raise ValueError("No CV uploaded for this profile")

    cv_path = profile.cv_path
    if not Path(cv_path).exists():
        raise ValueError("CV file not found on disk")

    try:
        cv_text = extract_text_from_pdf(cv_path)
    except Exception:
        logger.exception("Failed to extract text from CV: %s", cv_path)
        raise ValueError("Failed to read CV file")

    if not cv_text.strip():
        raise ValueError("CV file contains no readable text")

    if not settings.api_key:
        raise ValueError(
            "LLM API key not configured. Set API_KEY in .env to enable skill extraction."
        )

    skills = extract_skills_with_ai(cv_text)
    return ExtractedSkills(skills=skills)
