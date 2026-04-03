import logging
import time
import requests

logger = logging.getLogger(__name__)

def get_one_id(db_conn, table: str, where_sql: str = "", params: tuple | None = None) -> int:
    logger.info("Fetching one id from table=%s where_sql=%s params=%s", table, where_sql, params)
    params = params or ()
    where_sql = f"WHERE {where_sql}" if where_sql else ""
    with db_conn.cursor() as cur:
        query = f"SELECT id FROM {table} {where_sql} ORDER BY id LIMIT 1"
        logger.debug("Executing query: %s with params: %s", query, params)
        cur.execute(query, params)
        row = cur.fetchone()
        if not row:
            logger.error(
                "No rows found in %s with where_sql=%s params=%s",
                table, where_sql, params
            )
            raise RuntimeError(f"No rows found in {table}")
        logger.info("Found id=%s in table=%s", row[0], table)
        return int(row[0])


def _wait_until(url: str, timeout_s: float = 60.0, interval_s: float = 0.5) -> None:
    deadline = time.time() + timeout_s
    last_exc = None
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code < 500:
                return
        except Exception as exc:  # noqa: BLE001 - test harness
            last_exc = exc
        time.sleep(interval_s)
    raise RuntimeError(f"Service not ready at {url}. Last error: {last_exc!r}")
