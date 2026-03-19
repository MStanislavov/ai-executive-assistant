from datetime import datetime

from pydantic import BaseModel


class CoverLetterCreate(BaseModel):
    job_opportunity_id: str | None = None
    jd_text: str | None = None


class CoverLetterRead(BaseModel):
    id: str
    profile_id: str
    job_opportunity_id: str | None = None
    run_id: str | None = None
    content: str
    created_at: datetime
