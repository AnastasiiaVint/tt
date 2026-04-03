from pydantic import BaseModel


class HealthModel(BaseModel):
    status: str
    service: str
