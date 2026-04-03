import os
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml
import pytest
import psycopg2

# Ensure project root is importable when pytest rootdir is `tests/`.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from candidate.core.clients import (
    FindingsClient,
    HealthClient,
    ScannerClient,
    StatsClient,
    VulnerabilitiesClient,
)
from candidate.core.clients.api_base import HttpSession
from candidate.core.helpers import _wait_until, get_one_id


def _setup_logging() -> logging.Logger:
    """
    Configure test logging.
    """
    fmt = (
        f"[{{asctime}}.{{msecs:03.0f}}: {{levelname}}: {{threadName}}: {{funcName}}]: {{message}}"
    )
    datefmt = "%d-%m-%Y %H:%M:%S"
    logger = logging.getLogger(__name__)

    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "pytest.log"

    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt, style="{")
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Avoid duplicates on re-import (e.g., test discovery reloads).
    for h in list(root.handlers):
        if getattr(h, "_tt_logging_managed", False):
            root.removeHandler(h)

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler._tt_logging_managed = True  # type: ignore[attr-defined]

    file_handler = logging.FileHandler(str(log_path), mode="a", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    file_handler._tt_logging_managed = True  # type: ignore[attr-defined]

    root.addHandler(console_handler)
    root.addHandler(file_handler)
    return logger


logger = _setup_logging()


@dataclass(frozen=True)
class ServiceConfig:
    api_base_url: str
    ui_base_url: str
    scanner_url: str
    postgres_dsn: str


@pytest.fixture(scope="session")
def config() -> ServiceConfig:
    # Load env.yaml
    root_path = Path(__file__).resolve().parents[1]
    with open((root_path / "env.yaml"), "r", encoding="utf-8") as f:
        env_data = yaml.safe_load(f)
    local = env_data.get("local", {})

    api_base_url = local.get("api_base_url", "http://localhost:8000")
    ui_base_url = local.get("ui_base_url", "http://localhost:8000/")
    scanner_url = os.getenv("SCANNER_API_URL", "http://localhost:8001")

    # Allow env overrides but default to env.yaml values.
    postgres_host = local["postgres_host"]
    postgres_port = int(local["postgres_port"])
    postgres_db = local["postgres_db"]
    postgres_user = local["postgres_user"]
    postgres_password = local["postgres_password"]


    postgres_dsn = (
        f"host={postgres_host} port={postgres_port} dbname={postgres_db} "
        f"user={postgres_user} password={postgres_password}"
    )
    return ServiceConfig(
        api_base_url=api_base_url,
        ui_base_url=ui_base_url,
        scanner_url=scanner_url,
        postgres_dsn=postgres_dsn,
    )

@pytest.fixture(scope="session", autouse=True)
def services_ready(config: ServiceConfig) -> None:
    _wait_until(f"{config.api_base_url}/health")
    _wait_until(f"{config.scanner_url}/health")
    logger.info("Services are healthy: api=%s scanner=%s", config.api_base_url, config.scanner_url)


@pytest.fixture(scope="session")
def api_session(config: ServiceConfig) -> HttpSession:
    """
    Shared HTTP session to the Dashboard API using the configured base URL.
    """
    return HttpSession(config.api_base_url)


@pytest.fixture(scope="session")
def scanner_session(config: ServiceConfig) -> HttpSession:
    """
    Shared HTTP session to the Scanner API using the configured base URL.
    """
    return HttpSession(config.scanner_url)


@pytest.fixture(scope="session")
def db_conn(config: ServiceConfig):
    conn = psycopg2.connect(config.postgres_dsn)
    conn.autocommit = False
    try:
        yield conn
    finally:
        conn.close()

@pytest.fixture(scope="session")
def findings_client(api_session: HttpSession) -> FindingsClient:
    return FindingsClient(api_session)


@pytest.fixture(scope="session")
def stats_client(api_session: HttpSession) -> StatsClient:
    return StatsClient(api_session)


@pytest.fixture(scope="session")
def vulnerabilities_client(api_session: HttpSession) -> VulnerabilitiesClient:
    return VulnerabilitiesClient(api_session)


@pytest.fixture(scope="session")
def health_client(api_session: HttpSession) -> HealthClient:
    return HealthClient(api_session)


@pytest.fixture(scope="session")
def scanner_client(scanner_session: HttpSession) -> ScannerClient:
    return ScannerClient(scanner_session)


@pytest.fixture(scope="module")
def asset_id(db_conn):
    return get_one_id(db_conn, "assets", "is_active = TRUE")

@pytest.fixture(scope="module")
def vulnerability_id(db_conn):
    return get_one_id(db_conn, "vulnerabilities")
