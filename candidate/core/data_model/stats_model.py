from typing import Dict

from pydantic import BaseModel


class RiskScoreModel(BaseModel):
    risk_score: float
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    average_cvss: float


class SummaryModel(BaseModel):
    total_findings: int
    open_findings: int
    confirmed_findings: int
    in_progress_findings: int
    resolved_findings: int
    false_positive_findings: int
    by_severity: Dict[str, int]
    by_environment: Dict[str, int]
