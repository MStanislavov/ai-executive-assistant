import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.profile import UserProfile
from app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileRead

router = APIRouter(tags=["profiles"])


def _serialize_list(value: list[str] | None) -> str | None:
    """Serialize a list to JSON string for Text column storage."""
    if value is None:
        return None
    return json.dumps(value)


def _deserialize_list(value: str | None) -> list[str] | None:
    """Deserialize a JSON string from Text column to list."""
    if value is None:
        return None
    return json.loads(value)


def _profile_to_read(profile: UserProfile) -> ProfileRead:
    """Convert a SQLAlchemy UserProfile to a ProfileRead schema."""
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


@router.post("/profiles", response_model=ProfileRead, status_code=201)
async def create_profile(
    body: ProfileCreate,
    db: AsyncSession = Depends(get_db),
) -> ProfileRead:
    profile = UserProfile(
        name=body.name,
        targets=_serialize_list(body.targets),
        constraints=_serialize_list(body.constraints),
        skills=_serialize_list(body.skills),
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return _profile_to_read(profile)


@router.get("/profiles", response_model=list[ProfileRead])
async def list_profiles(
    db: AsyncSession = Depends(get_db),
) -> list[ProfileRead]:
    result = await db.execute(select(UserProfile).order_by(UserProfile.created_at))
    profiles = result.scalars().all()
    return [_profile_to_read(p) for p in profiles]


@router.get("/profiles/{profile_id}", response_model=ProfileRead)
async def get_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProfileRead:
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _profile_to_read(profile)


@router.put("/profiles/{profile_id}", response_model=ProfileRead)
async def update_profile(
    profile_id: str,
    body: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProfileRead:
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = body.model_dump(exclude_unset=True)
    for field in ("targets", "constraints", "skills"):
        if field in update_data:
            update_data[field] = _serialize_list(update_data[field])

    for key, value in update_data.items():
        setattr(profile, key, value)

    await db.commit()
    await db.refresh(profile)
    return _profile_to_read(profile)


@router.delete("/profiles/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    await db.delete(profile)
    await db.commit()


@router.post("/profiles/{profile_id}/cv", response_model=ProfileRead)
async def upload_cv(
    profile_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> ProfileRead:
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    cv_dir = settings.artifacts_dir / "cvs" / profile_id
    os.makedirs(cv_dir, exist_ok=True)

    file_path = cv_dir / (file.filename or "cv.pdf")
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    profile.cv_path = str(file_path)
    await db.commit()
    await db.refresh(profile)
    return _profile_to_read(profile)
