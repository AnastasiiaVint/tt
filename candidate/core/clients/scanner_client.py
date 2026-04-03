from typing import Any

from .api_base import Base, HttpSession, ResponseWrapper, step_methods


@step_methods
class ScannerClient(Base):
    SCANS_PATH = "/scans"
    HEALTH_PATH = "/health"

    def __init__(self, session: HttpSession) -> None:
        super().__init__(session)

    def create_scan(
        self,
        *,
        asset_id: int,
        scanner_name: str,
        vulnerability_ids: list[int],
    ) -> ResponseWrapper:
        payload: dict[str, Any] = {
            "asset_id": asset_id,
            "scanner_name": scanner_name,
            "vulnerability_ids": vulnerability_ids,
        }
        resp = self.session.post(self.SCANS_PATH, body=payload, timeout=10)
        return ResponseWrapper(resp)
