from .api_base import Base, HttpSession, ResponseWrapper, step_methods


@step_methods
class HealthClient(Base):
    HEALTH_PATH = "/health"

    def __init__(self, session: HttpSession) -> None:
        super().__init__(session)

    def health(self) -> ResponseWrapper:
        resp = self.session.get(self.HEALTH_PATH, timeout=10)
        return ResponseWrapper(resp)

