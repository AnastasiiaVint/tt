from playwright.sync_api import Locator, Page


class DashboardElements:
    def __init__(self, page: Page) -> None:
        self.page = page

    @property
    def title(self) -> Locator:
        return self.page.locator(".topbar h1")

    @property
    def total_count(self) -> Locator:
        return self.page.locator("#total-count")

    @property
    def findings_rows(self) -> Locator:
        return self.page.locator("#findings-table tr")

    def finding_row_by_id(self, finding_id: int) -> Locator:
        return self.page.locator("#findings-table tr", has_text=f"#{finding_id}").first


class DashboardPage:
    def __init__(self, page: Page, base_url: str = "http://localhost:8000/") -> None:
        self.page = page
        self.base_url = base_url.rstrip("/") + "/"
        self.elements = DashboardElements(self.page)

    def goto(self) -> None:
        self.page.goto(self.base_url, wait_until="domcontentloaded")
        self.wait_until_loaded()

    def wait_until_loaded(self) -> None:
        # JS renders asynchronously after the initial HTML load.
        self.page.wait_for_selector("#total-count", timeout=10000)
        self.page.wait_for_function(
            "document.querySelector('#total-count') && document.querySelector('#total-count').textContent !== '-'",
            timeout=30000,
        )
        self.page.wait_for_selector("#findings-table tr", timeout=30000)

    def title_text(self) -> str:
        return self.elements.title.inner_text().strip()

    def wait_for_finding_row(self, finding_id: int, timeout: int = 10000) -> Locator:
        row = self.elements.finding_row_by_id(finding_id)
        row.wait_for(timeout=timeout)
        return row

    @staticmethod
    def desired_badge_text(status: str) -> str:
        # UI displays status with underscores replaced by spaces.
        return status.replace("_", " ")

    def row_badge_text(self, row: Locator) -> str:
        return row.locator("span.status").first.inner_text().strip()

    def select_row_status(self, row: Locator, status: str) -> None:
        row.locator("select.status-select").first.select_option(status)
