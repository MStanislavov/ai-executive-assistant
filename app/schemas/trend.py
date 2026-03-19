from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TrendRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    run_id: str
    title: str
    category: str | None = None
    url: str | None = None
    description: str | None = None
    relevance: str | None = None
    source: str | None = None
    created_at: datetime
