"""Policy HTTP endpoints: list and get YAML policies."""

from fastapi import APIRouter, HTTPException

from app.schemas.policy import PolicyRead
from app.services import policy_service

router = APIRouter(tags=["policies"])


@router.get("/policies")
async def list_policies() -> list[PolicyRead]:
    return policy_service.list_policies()


@router.get(
    "/policies/{policy_name}",
    responses={404: {"description": "Policy not found"}},
)
async def get_policy(policy_name: str) -> PolicyRead:
    result = policy_service.get_policy(policy_name)
    if result is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return result
