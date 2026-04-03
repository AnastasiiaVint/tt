import allure

from candidate.core.data_model import HealthModel


def test_health_endpoint_returns_expected_schema_and_values(health_client):
    """
    Health endpoint smoke test.

    What we validate:
    - HTTP 200
    - Response schema via Pydantic (`HealthModel`)
    - Required keys/values: `status` and `service`
    """
    with allure.step("Call GET /health"):
        resp = health_client.health()
        assert resp.status_code == 200, resp.text

    with allure.step("Validate response via Pydantic"):
        model = resp.to_model(HealthModel)
        assert model.status == "healthy"
        assert model.service == "dashboard-api"

