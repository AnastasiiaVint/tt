import time

import allure
import pytest

from candidate.core.data_model.finding_model import FindingDetailModel
from candidate.core.helpers import get_one_id


def test_ui_dashboard_loads(dashboard_page):
    """
    UI smoke test for dashboard landing page.

    What we validate:
    - Dashboard page opens successfully
    - Main title matches expected product title
    - Screenshot is captured automatically on failure
    """
    with allure.step("Open dashboard page"):
        dashboard_page.goto()

    with allure.step("Validate dashboard title"):
        assert dashboard_page.title_text() == "Vulnerability Dashboard"


@pytest.mark.xfail(reason="BUG #5: UI does not refresh table after status update", strict=True)
def test_ui_status_change_is_reflected_in_table(findings_client, db_conn, dashboard_page):
    """
    UI integration test for status-change behavior in findings table.

    What we validate:
    - A new finding is created through API and appears in dashboard table
    - The initial row status badge is `open`
    - After changing status to `resolved`, UI should refresh row badge accordingly
      (currently expected to fail due to known bug #8)
    - Screenshot is captured automatically on failure
    """
    with allure.step("Prepare valid asset and vulnerability references from DB"):
        asset_id = get_one_id(db_conn, "assets", "is_active = TRUE")
        vulnerability_id = get_one_id(db_conn, "vulnerabilities")

    with allure.step("Create finding via API and parse response with data model"):
        unique_suffix = str(int(time.time() * 1000))
        create_resp = findings_client.create_finding(
            asset_id=asset_id,
            vulnerability_id=vulnerability_id,
            scanner="pytest-ui-status",
            notes=f"ui-status-{unique_suffix}",
        )
        finding_model = create_resp.to_model(FindingDetailModel)
        finding_id = finding_model.id

    with allure.step("Open dashboard page and locate created finding row"):
        dashboard_page.goto()
        row = dashboard_page.wait_for_finding_row(finding_id)

    with allure.step("Validate initial status badge is open"):
        assert dashboard_page.row_badge_text(row) == dashboard_page.desired_badge_text("open")

    with allure.step("Change row status to resolved"):
        dashboard_page.select_row_status(row, "resolved")

    with allure.step("Validate row badge reflects resolved status"):
        dashboard_page.page.wait_for_timeout(500)
        assert dashboard_page.row_badge_text(row) == dashboard_page.desired_badge_text("resolved")
