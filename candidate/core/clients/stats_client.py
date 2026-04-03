from .api_base import Base, HttpSession, ResponseWrapper, step_methods


@step_methods
class StatsClient(Base):
    RISK_SCORE_PATH = "/stats/risk-score"
    SUMMARY_PATH = "/stats/summary"

    def __init__(self, session: HttpSession) -> None:
        super().__init__(session)

    def get_risk_score(self) -> ResponseWrapper:
        resp = self.session.get(self.RISK_SCORE_PATH, timeout=10)
        return ResponseWrapper(resp)

    def get_summary(self) -> ResponseWrapper:
        resp = self.session.get(self.SUMMARY_PATH, timeout=10)
        return ResponseWrapper(resp)
