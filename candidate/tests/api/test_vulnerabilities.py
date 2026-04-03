import allure

from candidate.core.data_model import VulnerabilityModel


def test_list_vulnerabilities_returns_expected_schema(vulnerabilities_client):
    """
    Vulnerabilities list endpoint validation.

    What we validate:
    - HTTP 200
    - Response is a list of `VulnerabilityModel`
    - Required fields are present and types are correct
    """
    with allure.step("Call GET /vulnerabilities"):
        resp = vulnerabilities_client.list_vulnerabilities()
        assert resp.status_code == 200, resp.text

    with allure.step("Validate each item via Pydantic"):
        raw = resp.json()
        assert isinstance(raw, list)
        assert len(raw) > 0, "Seed data should include vulnerabilities"
        models = [VulnerabilityModel.model_validate(x) for x in raw]

    with allure.step("Sanity checks on parsed models"):
        for v in models:
            assert isinstance(v.id, int)
            assert v.cve_id.startswith("CVE-")
            assert v.severity in {"critical", "high", "medium", "low"}


def test_list_vulnerabilities_supports_severity_filter(vulnerabilities_client):
    """
    Vulnerabilities list supports `severity` query param.

    What we validate:
    - HTTP 200
    - All returned elements match the requested severity
    """
    severity = "critical"
    with allure.step(f"Call GET /vulnerabilities?severity={severity}"):
        resp = vulnerabilities_client.list_vulnerabilities(severity=severity)
        assert resp.status_code == 200, resp.text

    with allure.step("Validate that all items match severity"):
        raw = resp.json()
        models = [VulnerabilityModel.model_validate(x) for x in raw]
        assert len(models) > 0, "Expected at least one critical vulnerability in seed data"
        assert all(m.severity == severity for m in models)


def test_get_vulnerability_returns_schema_and_detail(vulnerabilities_client, db_conn):
    """
    Get vulnerability detail endpoint validation.

    What we validate:
    - HTTP 200 for an existing vulnerability
    - Response conforms to `VulnerabilityModel`
    - `GET /vulnerabilities/{id}` returns a matching id
    """
    with allure.step("Pick a vulnerability id from DB"):
        with db_conn.cursor() as cur:
            cur.execute("SELECT id FROM vulnerabilities ORDER BY id LIMIT 1")
            (vuln_id,) = cur.fetchone()

    with allure.step(f"Call GET /vulnerabilities/{vuln_id}"):
        resp = vulnerabilities_client.get_vulnerability(vuln_id)
        assert resp.status_code == 200, resp.text

    with allure.step("Validate response via Pydantic"):
        model = resp.to_model(VulnerabilityModel)
        assert model.id == vuln_id


def test_get_non_existent_vulnerability_returns_404(vulnerabilities_client):
    """
    Non-existent resource handling for vulnerabilities.

    What we validate:
    - HTTP 404
    - Error body includes `detail`
    """
    with allure.step("Call GET /vulnerabilities/{missing_id}"):
        missing_id = 99999999
        resp = vulnerabilities_client.get_vulnerability(missing_id)
        assert resp.status_code == 404, resp.text

    with allure.step("Validate error body"):
        body = resp.json()
        assert "detail" in body
