import allure

from candidate.core.data_model import RiskScoreModel, SummaryModel


def test_stats_risk_score_matches_schema_and_is_in_range(stats_client):
    """
    Risk score endpoint validation.

    What we validate:
    - HTTP 200
    - Response schema via Pydantic (`RiskScoreModel`)
    - Sanity/range checks:
      - `risk_score` should be within [0..10]
      - `total_findings` should be >= sum of severities counts
    """
    with allure.step("Call GET /stats/risk-score"):
        resp = stats_client.get_risk_score()
        assert resp.status_code == 200, resp.text

    with allure.step("Validate response schema via Pydantic"):
        model = resp.to_model(RiskScoreModel)

    with allure.step("Sanity checks"):
        assert 0.0 <= model.risk_score <= 10.0
        assert model.total_findings >= 0
        assert model.critical_count + model.high_count + model.medium_count + model.low_count >= 0
        # The implementation filters out resolved/false_positive; still, the counts should not exceed total.
        assert (
            model.critical_count + model.high_count + model.medium_count + model.low_count
        ) <= model.total_findings


def test_stats_summary_has_consistent_totals(stats_client):
    """
    Summary endpoint validation.

    What we validate:
    - HTTP 200
    - Response schema via Pydantic (`SummaryModel`)
    - Count consistency:
      - `total_findings` equals the sum of status buckets
    - Key/value sanity for dict fields
    """
    with allure.step("Call GET /stats/summary"):
        resp = stats_client.get_summary()
        assert resp.status_code == 200, resp.text

    with allure.step("Validate response schema via Pydantic"):
        model = resp.to_model(SummaryModel)

    with allure.step("Validate total status consistency"):
        status_sum = (
            model.open_findings
            + model.confirmed_findings
            + model.in_progress_findings
            + model.resolved_findings
            + model.false_positive_findings
        )
        assert model.total_findings == status_sum

    with allure.step("Validate dict fields shape"):
        assert isinstance(model.by_severity, dict)
        assert isinstance(model.by_environment, dict)

        allowed_severities = {"critical", "high", "medium", "low"}
        assert set(model.by_severity.keys()).issubset(allowed_severities)
        assert all(isinstance(v, int) and v >= 0 for v in model.by_severity.values())

        allowed_env = {"production", "staging", "development"}
        # In schema those are constrained, but DB might have additional data in future seeds.
        assert set(model.by_environment.keys()).issubset(allowed_env)
        assert all(isinstance(v, int) and v >= 0 for v in model.by_environment.values())

