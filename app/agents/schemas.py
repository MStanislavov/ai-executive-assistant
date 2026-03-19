"""Pydantic schemas for LLM structured output from agents."""

from pydantic import BaseModel, Field


# -- GoalExtractor output --

class GoalExtractorOutput(BaseModel):
    cert_prompt: str = Field(description="Full directive sentence to find certifications and courses, e.g. 'Search for AWS certifications and architecture courses for a Java developer'")
    event_prompt: str = Field(description="Full directive sentence to find events and conferences, e.g. 'Find 2026 software architecture and AI conferences in Europe'")
    group_prompt: str = Field(description="Full directive sentence to find professional communities and groups, e.g. 'Search Discord, Reddit, and LinkedIn for Java and cloud computing communities'")
    job_prompt: str = Field(description="Full directive sentence to find job openings, e.g. 'Search for senior Java and Python developer job openings'")
    trend_prompt: str = Field(description="Full directive sentence to find trends, e.g. 'Find emerging trends in cloud-native architecture and AI engineering'")


# -- WebScraper output --

class WebScraperResult(BaseModel):
    title: str = Field(description="Title of the search result")
    url: str = Field(default="", description="URL of the search result")
    snippet: str = Field(default="", description="Brief excerpt or description")
    source: str = Field(default="", description="Source website or domain")


class WebScraperOutput(BaseModel):
    results: list[WebScraperResult] = Field(default_factory=list)


# -- DataFormatter sub-models --

class FormattedJob(BaseModel):
    title: str
    company: str | None = None
    url: str | None = None
    description: str | None = None
    location: str | None = None
    salary_range: str | None = None

class FormattedCertification(BaseModel):
    title: str
    provider: str | None = None
    url: str | None = None
    description: str | None = None
    cost: str | None = None
    duration: str | None = None

class FormattedCourse(BaseModel):
    title: str
    platform: str | None = None
    url: str | None = None
    description: str | None = None
    cost: str | None = None
    duration: str | None = None

class FormattedEvent(BaseModel):
    title: str
    organizer: str | None = None
    url: str | None = None
    description: str | None = None
    event_date: str | None = None
    location: str | None = None

class FormattedGroup(BaseModel):
    title: str
    platform: str | None = None
    url: str | None = None
    description: str | None = None
    member_count: int | None = None

class FormattedTrend(BaseModel):
    title: str
    category: str | None = None
    url: str | None = None
    description: str | None = None
    relevance: str | None = None
    source: str | None = None

class DataFormatterOutput(BaseModel):
    jobs: list[FormattedJob] = Field(default_factory=list)
    certifications: list[FormattedCertification] = Field(default_factory=list)
    courses: list[FormattedCourse] = Field(default_factory=list)
    events: list[FormattedEvent] = Field(default_factory=list)
    groups: list[FormattedGroup] = Field(default_factory=list)
    trends: list[FormattedTrend] = Field(default_factory=list)


# -- CEO output --

class StrategicRecommendation(BaseModel):
    area: str = Field(description="Area of recommendation (e.g. 'career move', 'skill gap')")
    recommendation: str = Field(description="Actionable recommendation")
    priority: str = Field(description="high, medium, or low")

class CEOOutput(BaseModel):
    strategic_recommendations: list[StrategicRecommendation] = Field(default_factory=list)
    ceo_summary: str = Field(description="Executive summary of strategic outlook")


# -- CFO output --

class RiskAssessment(BaseModel):
    area: str = Field(description="Area being assessed")
    risk_level: str = Field(description="low, medium, or high")
    time_investment: str = Field(description="Estimated time commitment")
    roi_estimate: str = Field(description="low, medium, or high")

class CFOOutput(BaseModel):
    risk_assessments: list[RiskAssessment] = Field(default_factory=list)
    cfo_summary: str = Field(description="Financial/risk summary")
