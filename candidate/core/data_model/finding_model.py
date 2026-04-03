from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from candidate.core.data_model.vulnerabilities import VulnerabilityModel


class FindingModel(BaseModel):
    id: int
    asset_id: int
    vulnerability_id: int
    status: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    scanner: Optional[str] = None
    notes: Optional[str] = None
    is_dismissed: bool


class FindingDetailModel(FindingModel):
    vulnerability: Optional[VulnerabilityModel] = None
    asset_hostname: Optional[str] = None


class PaginatedFindingsModel(BaseModel):
    items: List[FindingModel]
    total: int
    page: int
    per_page: int


class FindingSearchResultModel(BaseModel):
    finding_id: int
    status: str
    scanner: str
    cve_id: str
    severity: str
    hostname: str
