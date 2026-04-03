import pytest
import allure

from candidate.core.ui import DashboardPage


@pytest.fixture()
def dashboard_page(page, config):
    return DashboardPage(page=page, base_url=config.api_base_url)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or report.passed:
        return

    page = item.funcargs.get("page")
    if page is None:
        return

    image_bytes = page.screenshot(full_page=True)
    allure.attach(
        image_bytes,
        name=f"{item.name}-failed",
        attachment_type=allure.attachment_type.PNG,
    )

