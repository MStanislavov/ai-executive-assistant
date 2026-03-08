"""Policies page: display all policy YAML files in accordion."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config import settings

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


@router.get("/policies")
async def policies_page(request: Request):
    policy_dir = settings.policy_dir
    policies: list[dict] = []
    if policy_dir.is_dir():
        for path in sorted(policy_dir.glob("*.yaml")):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            policies.append({"name": path.stem, "content": content})

    return templates.TemplateResponse("policies.html", {
        "request": request,
        "policies": policies,
    })
