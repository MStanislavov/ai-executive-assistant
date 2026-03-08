from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.schemas.policy import PolicyRead

router = APIRouter(tags=["policies"])


def _load_policy(path: Path) -> dict:
    """Load and parse a YAML policy file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@router.get("/policies", response_model=list[PolicyRead])
async def list_policies() -> list[PolicyRead]:
    policy_dir = settings.policy_dir
    if not policy_dir.is_dir():
        return []
    policies: list[PolicyRead] = []
    for path in sorted(policy_dir.glob("*.yaml")):
        policies.append(
            PolicyRead(name=path.stem, content=_load_policy(path))
        )
    return policies


@router.get("/policies/{policy_name}", response_model=PolicyRead)
async def get_policy(policy_name: str) -> PolicyRead:
    path = settings.policy_dir / f"{policy_name}.yaml"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Policy not found")
    return PolicyRead(name=policy_name, content=_load_policy(path))
