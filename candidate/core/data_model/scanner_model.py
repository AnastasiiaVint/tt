from pydantic import BaseModel


class ScanResultModel(BaseModel):
    id: int
    asset_id: int
    scanner_name: str
    status: str
    findings_count: int
