from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class VulnerabilityModel(BaseModel):
    id: int
    cve_id: str
    title: str
    description: Optional[str] = None
    severity: str
    cvss_score: Optional[float] = None
    published_date: Optional[datetime] = None
    created_at: datetime
