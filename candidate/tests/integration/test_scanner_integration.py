import time
from concurrent.futures import ThreadPoolExecutor

import allure
from candidate.core.data_model.finding_model import FindingDetailModel, PaginatedFindingsModel
from candidate.core.data_model.scanner_model import ScanResultModel


def _get_first_n_ids(db_conn, table: str, n: int) -> list[int]:
    with db_conn.cursor() as cur:
        cur.execute(f"SELECT id FROM {table} ORDER BY id LIMIT %s", (n,))
        rows = cur.fetchall()
    return [int(r[0]) for r in rows]


def test_scan_creates_findings_in_dashboard(scanner_client, db_conn, findings_client, asset_id):
    """
    Validate cross-service scan import flow.

    What we validate:
    - Scanner Service accepts a scan import request
    - Findings are persisted in DB for the imported vulnerabilities
    - Dashboard API returns findings created by the scan
    """
    with allure.step("Prepare scan input data"):
        vulnerability_ids = _get_first_n_ids(db_conn, "vulnerabilities", 2)
        assert len(vulnerability_ids) == 2

        unique_suffix = str(int(time.time() * 1000))
        scanner_name = f"pytest-scan-{unique_suffix}"

    with allure.step("Verify there are no findings for this scanner before import"):
        with db_conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM findings
                WHERE asset_id = %s AND vulnerability_id = ANY(%s) AND scanner = %s
                """,
                (asset_id, vulnerability_ids, scanner_name),
            )
            (before_count,) = cur.fetchone()
        assert before_count == 0

    with allure.step("Run scan import via Scanner Service API"):
        resp = scanner_client.create_scan(
            asset_id=asset_id,
            scanner_name=scanner_name,
            vulnerability_ids=vulnerability_ids,
        )
        assert resp.status_code == 201, resp.text
        scan_model = resp.to_model(ScanResultModel)
        assert scan_model.status == "completed"
        assert scan_model.findings_count == 2

    with allure.step("Verify imported findings exist in DB"):
        with db_conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM findings
                WHERE asset_id = %s AND vulnerability_id = ANY(%s) AND scanner = %s AND is_dismissed = FALSE
                """,
                (asset_id, vulnerability_ids, scanner_name),
            )
            (after_count,) = cur.fetchone()
        assert after_count == 2

    with allure.step("Verify imported findings are visible in Dashboard API"):
        dashboard_resp = findings_client.list_findings(asset_id=asset_id, per_page=50, page=1)
        assert dashboard_resp.status_code == 200, dashboard_resp.text
        page_model = dashboard_resp.to_model(PaginatedFindingsModel)
        assert any(item.scanner == scanner_name for item in page_model.items)


def test_scan_findings_can_be_updated_via_api(scanner_client, db_conn, findings_client, asset_id):
    """
    Validate that findings created by Scanner can be updated through Dashboard API.

    What we validate:
    - A scan import creates at least one finding
    - Updating finding status via Dashboard API succeeds
    - DB state is consistent with API update (status and resolved_at)
    """
    with allure.step("Import a single finding via Scanner Service"):
        vulnerability_ids = _get_first_n_ids(db_conn, "vulnerabilities", 1)
        vuln_id = vulnerability_ids[0]

        unique_suffix = str(int(time.time() * 1000))
        scanner_name = f"pytest-scan-update-{unique_suffix}"

        scan_resp = scanner_client.create_scan(
            asset_id=asset_id,
            scanner_name=scanner_name,
            vulnerability_ids=[vuln_id],
        )
        assert scan_resp.status_code == 201, scan_resp.text
        scan_model = scan_resp.to_model(ScanResultModel)
        assert scan_model.findings_count == 1

    with allure.step("Fetch created finding id from DB"):
        with db_conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM findings
                WHERE asset_id = %s AND vulnerability_id = %s AND scanner = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (asset_id, vuln_id, scanner_name),
            )
            (finding_id,) = cur.fetchone()

    with allure.step("Update finding status via Dashboard API"):
        update_resp = findings_client.update_finding_status(
            finding_id,
            status="resolved",
            notes=f"resolved-by-test-{unique_suffix}",
        )
        updated_model = update_resp.to_model(FindingDetailModel)
        assert updated_model.status == "resolved"
        assert updated_model.resolved_at is not None

    with allure.step("Verify DB matches updated finding state"):
        with db_conn.cursor() as cur:
            cur.execute("SELECT status, resolved_at FROM findings WHERE id = %s", (finding_id,))
            row = cur.fetchone()
        assert row[0] == "resolved"
        assert row[1] is not None


def test_concurrent_scan_imports_create_findings_consistently(
    scanner_client,
    db_conn,
    findings_client,
    asset_id,
):
    """
    Validate concurrent scan imports across Scanner and Dashboard services.

    What we validate:
    - Two scan imports can run concurrently without data loss
    - DB contains findings created by each concurrent import
    - Dashboard API exposes findings from both scanner runs
    """
    with allure.step("Prepare vulnerability ids and unique scanner names"):
        vulnerability_ids = _get_first_n_ids(db_conn, "vulnerabilities", 1)
        vuln_id = vulnerability_ids[0]
        unique_suffix = str(int(time.time() * 1000))
        scanner_names = [f"pytest-concurrent-{unique_suffix}-a", f"pytest-concurrent-{unique_suffix}-b"]

    with allure.step("Run concurrent scan imports"):
        def _import_scan(scanner_name: str):
            response = scanner_client.create_scan(
                asset_id=asset_id,
                scanner_name=scanner_name,
                vulnerability_ids=[vuln_id],
            )
            assert response.status_code == 201, response.text
            scan_model = response.to_model(ScanResultModel)
            assert scan_model.status == "completed"
            assert scan_model.findings_count == 1

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(_import_scan, name) for name in scanner_names]
            for future in futures:
                future.result()

    with allure.step("Verify DB has findings for both concurrent scanner names"):
        with db_conn.cursor() as cur:
            cur.execute(
                """
                SELECT scanner, COUNT(*)
                FROM findings
                WHERE asset_id = %s
                  AND vulnerability_id = %s
                  AND scanner = ANY(%s)
                GROUP BY scanner
                """,
                (asset_id, vuln_id, scanner_names),
            )
            rows = cur.fetchall()
        counts_by_scanner = {row[0]: int(row[1]) for row in rows}
        assert all(counts_by_scanner.get(name, 0) >= 1 for name in scanner_names)

    with allure.step("Verify Dashboard API lists findings from concurrent imports"):
        dashboard_resp = findings_client.list_findings(asset_id=asset_id, per_page=100, page=1)
        assert dashboard_resp.status_code == 200, dashboard_resp.text
        page_model = dashboard_resp.to_model(PaginatedFindingsModel)
        found_scanners = {item.scanner for item in page_model.items}
        assert all(name in found_scanners for name in scanner_names)
