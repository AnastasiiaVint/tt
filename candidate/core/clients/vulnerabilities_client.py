from typing import Any, Optional

from .api_base import Base, HttpSession, ResponseWrapper, step_methods


@step_methods
class VulnerabilitiesClient(Base):
    PATH = "/vulnerabilities"

    def __init__(self, session: HttpSession) -> None:
        super().__init__(session)

    def list_vulnerabilities(self, *, severity: Optional[str] = None) -> ResponseWrapper:
        params: dict[str, Any] = {}
        if severity:
            params["severity"] = severity

        resp = self.session.get(self.PATH, params=params or None, timeout=10)
        return ResponseWrapper(resp)

    def get_vulnerability(self, vuln_id: int) -> ResponseWrapper:
        resp = self.session.get(f"{self.PATH}/{vuln_id}", timeout=10)
        return ResponseWrapper(resp)
