import time

import allure
import psycopg2
import pytest

from candidate.core.helpers import get_one_id


def test_dismiss_finding_reflected_in_database(findings_client, db_conn):
    """
    Test description:
        Verify data integrity after dismissing a finding through API.
    Steps:
        1. Get valid asset and vulnerability IDs from DB.
        2. Create a finding via API.
        3. Dismiss the created finding via API.
        4. Query DB for is_dismissed value of the same finding.
    Expected result:
        The finding exists in DB and is_dismissed is TRUE.
    """
    with allure.step("Prepare valid asset and vulnerability references"):
        asset_id = get_one_id(db_conn, "assets", "is_active = TRUE")
        vulnerability_id = get_one_id(db_conn, "vulnerabilities")

    with allure.step("Create a finding via API"):
        unique_suffix = str(int(time.time() * 1000))
        created = findings_client.create_finding(
            asset_id=asset_id,
            vulnerability_id=vulnerability_id,
            scanner="pytest-db-dismiss",
            notes=f"db-dismiss-{unique_suffix}",
        ).json()

    with allure.step("Dismiss the created finding via API"):
        dismiss_resp = findings_client.dismiss_finding(created["id"])
        assert dismiss_resp.status_code == 204

    with allure.step("Validate in DB that finding is marked dismissed"):
        with db_conn.cursor() as cur:
            cur.execute("SELECT is_dismissed FROM findings WHERE id = %s", (created["id"],))
            row = cur.fetchone()
    assert row is not None
    assert row[0] is True


def test_created_finding_references_assets_and_vulnerabilities(findings_client, db_conn):
    """
    Test description:
        Validate referential consistency between findings, assets, and vulnerabilities.
    Steps:
        1. Get valid asset and vulnerability IDs from DB.
        2. Create a finding via API.
        3. Execute DB join across findings, assets, vulnerabilities for created finding.
        4. Verify joined record is returned.
    Expected result:
        Created finding has valid references to existing asset and vulnerability records.
    """
    with allure.step("Prepare valid asset and vulnerability references"):
        asset_id = get_one_id(db_conn, "assets", "is_active = TRUE")
        vulnerability_id = get_one_id(db_conn, "vulnerabilities")

    with allure.step("Create a finding via API"):
        created = findings_client.create_finding(
            asset_id=asset_id,
            vulnerability_id=vulnerability_id,
            scanner="pytest-db-integrity",
            notes="db-integrity",
        ).json()

    with allure.step("Join findings with assets and vulnerabilities in DB"):
        with db_conn.cursor() as cur:
            cur.execute(
                """
                SELECT f.id
                FROM findings f
                JOIN assets a ON a.id = f.asset_id
                JOIN vulnerabilities v ON v.id = f.vulnerability_id
                WHERE f.id = %s AND a.id IS NOT NULL AND v.id IS NOT NULL
                """,
                (created["id"],),
            )
            row = cur.fetchone()
    assert row is not None
    assert int(row[0]) == created["id"]


@pytest.mark.xfail(
    reason="BUG #4: vulnerabilities.cvss_score has no CHECK constraint for 0-10 range", strict=True
)
def test_cvss_score_out_of_range_rejected_by_db(db_conn):
    """
    Test description:
        Check DB constraint for CVSS score range enforcement.
    Steps:
        1. Generate unique vulnerability identifier.
        2. Try to insert vulnerability with out-of-range cvss_score value (999.0).
        3. Observe DB behavior and rollback transaction.
    Expected result:
        DB raises IntegrityError for out-of-range cvss_score.
        This test is marked xfail because known bug allows invalid value.
    """
    with allure.step("Prepare unique vulnerability test data"):
        cve_id = f"CVE-TEST-CVSS-{int(time.time())}"

    with allure.step("Insert vulnerability with out-of-range CVSS and verify rejection"):
        with db_conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO vulnerabilities 
                    (cve_id, title, description, severity, cvss_score, published_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (cve_id, "out-of-range cvss", "should fail", "medium", 999.0, "2024-01-01"),
                )
                # No error means the constraint is missing.
                db_conn.rollback()
                pytest.fail("Expected an IntegrityError due to cvss_score range constraint")
            except psycopg2.IntegrityError:
                db_conn.rollback()


def test_db_enforces_required_fields_for_vulnerabilities(db_conn):
    """
    Test description:
        Verify DB enforces required fields in vulnerabilities table.
    Steps:
        1. Generate unique vulnerability identifier.
        2. Attempt to insert vulnerability with NULL title.
        3. Capture DB exception and rollback transaction.
    Expected result:
        DB raises IntegrityError because title is required (NOT NULL).
    """
    with allure.step("Prepare unique vulnerability identifier"):
        cve_id = f"CVETNULL{int(time.time()) % 1000000:06d}"

    with allure.step("Insert vulnerability with NULL title and verify DB constraint"):
        with db_conn.cursor() as cur:
            with pytest.raises(psycopg2.IntegrityError):
                cur.execute(
                    """
                    INSERT INTO vulnerabilities (cve_id, title, description, severity, cvss_score, published_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (cve_id, None, "missing title", "low", 1.0, "2024-01-01"),
                )
            db_conn.rollback()
