from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    run_id: str
    title: str
    organizer: str | None = None
    url: str | None = None
    description: str | None = None
    event_date: str | None = None
    location: str | None = None
    created_at: datetime
