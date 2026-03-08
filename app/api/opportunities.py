"""Opportunities API: list and retrieve opportunities scoped to a profile."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.opportunity import Opportunity
from app.schemas.opportunity import OpportunityRead

router = APIRouter(tags=["opportunities"])


def _opp_to_read(opp: Opportunity) -> OpportunityRead:
    """Convert a SQLAlchemy Opportunity to an OpportunityRead schema."""
    return OpportunityRead(
        id=opp.id,
        profile_id=opp.profile_id,
        run_id=opp.run_id,
        opportunity_type=opp.opportunity_type,
        title=opp.title,
        source=opp.source,
        url=opp.url,
        description=opp.description,
        evidence_ids=json.loads(opp.evidence_ids_json) if opp.evidence_ids_json else [],
        metadata=json.loads(opp.metadata_json) if opp.metadata_json else None,
        created_at=opp.created_at,
    )


@router.get(
    "/profiles/{profile_id}/opportunities",
    response_model=list[OpportunityRead],
)
async def list_opportunities(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[OpportunityRead]:
    result = await db.execute(
        select(Opportunity)
        .where(Opportunity.profile_id == profile_id)
        .order_by(Opportunity.created_at.desc())
    )
    opps = result.scalars().all()
    return [_opp_to_read(o) for o in opps]


@router.get(
    "/profiles/{profile_id}/opportunities/{opportunity_id}",
    response_model=OpportunityRead,
)
async def get_opportunity(
    profile_id: str,
    opportunity_id: str,
    db: AsyncSession = Depends(get_db),
) -> OpportunityRead:
    opp = await db.get(Opportunity, opportunity_id)
    if opp is None or opp.profile_id != profile_id:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return _opp_to_read(opp)
