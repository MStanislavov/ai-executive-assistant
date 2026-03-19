"""Profile HTTP endpoints: CRUD, CV upload, skill extraction."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.error_messages import profile_not_found
from app.db import get_db
from app.schemas.profile import ProfileCreate, ProfileRead, ProfileUpdate
from app.services import profile_service
from app.services.profile_service import ExtractedSkills

router = APIRouter(tags=["profiles"])


@router.post("/profiles", status_code=201)
async def create_profile(
    body: ProfileCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileRead:
    return await profile_service.create_profile(db, body)


@router.get("/profiles")
async def list_profiles(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ProfileRead]:
    return await profile_service.list_profiles(db)


@router.get(
    "/profiles/{profile_id}",
    responses={404: {"description": profile_not_found}},
)
async def get_profile(
    profile_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileRead:
    result = await profile_service.get_profile(db, profile_id)
    if result is None:
        raise HTTPException(status_code=404, detail=profile_not_found)
    return result


@router.put(
    "/profiles/{profile_id}",
    responses={404: {"description": profile_not_found}},
)
async def update_profile(
    profile_id: str,
    body: ProfileUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileRead:
    result = await profile_service.update_profile(db, profile_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail=profile_not_found)
    return result


@router.delete(
    "/profiles/{profile_id}",
    status_code=204,
    responses={404: {"description": profile_not_found}},
)
async def delete_profile(
    profile_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    deleted = await profile_service.delete_profile(db, profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=profile_not_found)


@router.post(
    "/profiles/{profile_id}/cv",
    responses={404: {"description": profile_not_found}},
)
async def upload_cv(
    profile_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
) -> ProfileRead:
    content = await file.read()
    result = await profile_service.upload_cv(
        db, profile_id, file.filename or "cv.pdf", content
    )
    if result is None:
        raise HTTPException(status_code=404, detail=profile_not_found)
    return result


@router.post(
    "/profiles/{profile_id}/cv/extract-skills",
    responses={
        404: {"description": profile_not_found},
        400: {"description": "No CV uploaded for this profile"},
    },
)
async def extract_skills_from_cv(
    profile_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExtractedSkills:
    try:
        return await profile_service.extract_skills_from_cv(db, profile_id)
    except LookupError:
        raise HTTPException(status_code=404, detail=profile_not_found)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
