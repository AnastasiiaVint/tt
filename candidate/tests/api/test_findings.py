import time

import pytest

from candidate.core.data_model.finding_model import (
    FindingDetailModel,
    PaginatedFindingsModel,
    FindingSearchResultModel,
)


def test_create_get_update_and_dismiss_happy_path(
    findings_client,
    asset_id,
    vulnerability_id,
    db_conn,
):
    """ Test the full lifecycle of a finding: create, get details, update status, and dismiss."""
    unique_suffix = str(int(time.time() * 1000))
    scanner = f"pytest-suite-{unique_suffix}"
    notes = f"notes-{unique_suffix}"

    # Create finding
    created_resp = findings_client.create_finding(
        asset_id=asset_id,
        vulnerability_id=vulnerability_id,
        scanner=scanner,
        notes=notes,
    )
    assert created_resp.status_code == 201
    created_finding_model = created_resp.to_model(FindingDetailModel)
    finding_id = created_finding_model.id


    # TODO: implement general validation methods for API response models
    assert created_finding_model.status == "open"
    assert created_finding_model.is_dismissed is False
    assert created_finding_model.resolved_at is None
    assert created_finding_model.asset_id == asset_id
    assert created_finding_model.vulnerability_id == vulnerability_id
    assert created_finding_model.scanner == scanner
    assert created_finding_model.notes == notes

    # GET detail
    detail_resp = findings_client.get_finding(finding_id)
    assert detail_resp.status_code == 200
    detail_model = detail_resp.to_model(FindingDetailModel)
    assert detail_model.id == finding_id
    assert detail_model.status == "open"
    assert detail_model.is_dismissed is False
    assert detail_model.vulnerability is not None
    assert detail_model.vulnerability.id == vulnerability_id
    assert detail_model.asset_hostname is not None

    # Update status
    updated_resp = findings_client.update_finding_status(
        finding_id=finding_id,
        status="confirmed",
        notes=f"updated-{unique_suffix}",
    )
    assert updated_resp.status_code == 200
    updated_model = updated_resp.to_model(FindingDetailModel)

    assert updated_model.id == finding_id
    assert updated_model.status == "confirmed"
    assert updated_model.resolved_at is None
    assert updated_model.notes == f"updated-{unique_suffix}"

    # Dismiss via API
    dismiss_resp = findings_client.dismiss_finding(finding_id)
    assert dismiss_resp.status_code == 204

    with db_conn.cursor() as cur:
        cur.execute("SELECT is_dismissed FROM findings WHERE id = %s", (finding_id,))
        is_dismissed = cur.fetchone()[0]
    assert is_dismissed is True

    # Dismissed findings should not appear in list endpoint
    list_resp = findings_client.list_findings(page=1, per_page=50)
    assert list_resp.status_code == 200
    page_model = list_resp.to_model(PaginatedFindingsModel)
    assert all(item.id != finding_id for item in page_model.items)


def test_update_finding_rejects_invalid_status(findings_client, asset_id, vulnerability_id):
    created = findings_client.create_finding(
        asset_id=asset_id,
        vulnerability_id=vulnerability_id,
        scanner="pytest-invalid-status",
        notes="invalid-status-test",
    ).json()

    resp = findings_client.update_finding_status(
        created["id"],
        status="totally_not_a_status",
    )
    assert resp.status_code == 400, resp.text
    assert "Invalid status" in resp.json()["detail"]


def test_create_finding_rejects_invalid_references(findings_client):
    resp = findings_client.create_finding(
        asset_id=999999,
        vulnerability_id=1,
        scanner="pytest",
        notes="bad-asset",
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Asset not found"

    resp = findings_client.create_finding(
        asset_id=1,
        vulnerability_id=999999,
        scanner="pytest",
        notes="bad-vuln",
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Vulnerability not found"


def test_non_existent_finding_endpoints(findings_client):
    missing_id = 99999999

    resp = findings_client.get_finding(missing_id)
    assert resp.status_code == 404

    resp = findings_client.update_finding_status(missing_id, status="open")
    assert resp.status_code == 404

    resp = findings_client.dismiss_finding(missing_id)
    assert resp.status_code == 404


def test_findings_pagination_boundaries(findings_client, asset_id, vulnerability_id):

    findings_client.create_finding(
        asset_id=asset_id,
        vulnerability_id=vulnerability_id,
        scanner="pytest-pagination",
        notes="pagination-test",
    )

    resp = findings_client.list_findings(page=1, per_page=100)
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["page"] == 1
    assert payload["per_page"] == 100
    assert len(payload["items"]) <= 100

    resp = findings_client.list_findings(page=1, per_page=101)
    assert resp.status_code == 422, resp.text


def test_search_findings_by_notes(findings_client, asset_id, vulnerability_id):

    unique_suffix = str(int(time.time() * 1000))
    created = findings_client.create_finding(
        asset_id=asset_id,
        vulnerability_id=vulnerability_id,
        scanner="pytest-search",
        notes=f"search-notes-{unique_suffix}",
    ).json()

    results_resp = findings_client.search_findings(q=f"search-notes-{unique_suffix}")
    assert results_resp.status_code == 200, results_resp.text
    results = [FindingSearchResultModel.model_validate(r) for r in results_resp.json()]
    assert any(r.finding_id == created["id"] for r in results)


def test_search_endpoint_empty_query_returns_empty_list(findings_client):
    resp = findings_client.search_findings(q="")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


@pytest.mark.xfail(
    reason="BUG #1: GET /findings/{id} does not filter out dismissed findings",
    strict=True
)
def test_get_dismissed_finding_returns_404(findings_client, asset_id, vulnerability_id):

    created = findings_client.create_finding(
        asset_id=asset_id,
        vulnerability_id=vulnerability_id,
        scanner="pytest-dismissed-get",
        notes="dismissed-get",
    ).json()
    findings_client.dismiss_finding(created["id"])

    # Desired behavior: 404 for dismissed findings
    resp = findings_client.get_finding(created["id"])
    assert resp.status_code == 404, resp.text


@pytest.mark.xfail(reason="BUG #2: update status transitions are not validated", strict=True)
def test_update_status_validates_transitions(findings_client, asset_id, vulnerability_id):

    created = findings_client.create_finding(
        asset_id=asset_id,
        vulnerability_id=vulnerability_id,
        scanner="pytest-transition",
        notes="transition-test",
    ).json()

    # Resolve first (allowed)
    findings_client.update_finding_status(created["id"], status="resolved", notes=None)

    # Desired behavior: resolved -> open should be rejected
    resp = findings_client.update_finding_status(created["id"], status="open", notes=None)
    assert resp.status_code == 400, resp.text


@pytest.mark.xfail(
    reason="BUG #3: /findings/search is built using a raw SQL f-string (SQL injection risk)",
    strict=True
)
def test_search_does_not_allow_sql_injection(findings_client):
    # Payload attempts to break out of the LIKE string and force a tautology.
    # If the implementation is vulnerable, this typically returns many results (not an empty list).
    resp = findings_client.search_findings(q="%' OR 1=1 -- ")
    assert resp.status_code == 200, resp.text
    assert resp.json() == [], "Expected empty results for an injection payload"

