from typing import Any, Optional

from .api_base import Base, HttpSession, ResponseWrapper, step_methods


@step_methods
class FindingsClient(Base):
    FINDING_PATH = "/findings"
    SEARCH_PATH = "/search"

    def __init__(self, session: HttpSession) -> None:
        super().__init__(session)

    def list_findings(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        asset_id: Optional[int] = None,
    ) -> ResponseWrapper:
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if status:
            params["status"] = status
        if severity:
            params["severity"] = severity
        if asset_id:
            params["asset_id"] = asset_id

        resp = self.session.get(self.FINDING_PATH, params=params, timeout=10)
        return ResponseWrapper(resp)

    def get_finding(self, finding_id: int) -> ResponseWrapper:
        resp = self.session.get(f"{self.FINDING_PATH}/{finding_id}", timeout=10)
        return ResponseWrapper(resp)

    def create_finding(
        self,
        *,
        asset_id: int,
        vulnerability_id: int,
        scanner: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> ResponseWrapper:
        payload: dict[str, Any] = {
            "asset_id": asset_id,
            "vulnerability_id": vulnerability_id,
            "scanner": scanner,
            "notes": notes,
        }
        # Remove nulls to better match API expectations.
        payload = {k: v for k, v in payload.items() if v is not None}
        resp = self.session.post(self.FINDING_PATH, body=payload, timeout=10)
        return ResponseWrapper(resp)

    def update_finding_status(
        self,
        finding_id: int,
        *,
        status: str,
        notes: Optional[str] = None,
    ) -> ResponseWrapper:
        payload: dict[str, Any] = {"status": status}
        if notes is not None:
            payload["notes"] = notes
        resp = self.session.put(f"{self.FINDING_PATH}/{finding_id}/status", body=payload, timeout=10)
        return ResponseWrapper(resp)

    def dismiss_finding(self, finding_id: int) -> ResponseWrapper:
        resp = self.session.delete(f"{self.FINDING_PATH}/{finding_id}", timeout=10)
        return ResponseWrapper(resp)

    def search_findings(self, *, q: str) -> ResponseWrapper:
        resp = self.session.get(f"{self.FINDING_PATH}{self.SEARCH_PATH}", params={"q": q}, timeout=10)
        return ResponseWrapper(resp)

