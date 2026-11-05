import asyncio
import contextlib

from playwright import async_api
from playwright.async_api import expect


async def run_test():
    pw = None
    browser = None
    context = None

    try:
        # Start a Playwright session in asynchronous mode
        pw = await async_api.async_playwright().start()

        # Launch a Chromium browser in headless mode with custom arguments
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--window-size=1280,720",
                "--disable-dev-shm-usage",
                "--ipc=host",
                "--single-process",
            ],
        )

        # Create a new browser context (like an incognito window)
        context = await browser.new_context()
        # Wider default timeout to match the agent's DOM-stability budget;
        # auto-waiting Playwright APIs (expect, locator.wait_for) inherit this.
        context.set_default_timeout(15000)

        # Open a new page in the browser context
        page = await context.new_page()

        # Interact with the page elements to simulate user flow
        # -> navigate
        await page.goto("http://localhost:5173/")
        with contextlib.suppress(Exception):
            await page.wait_for_load_state("domcontentloaded", timeout=5000)

        # -> Click “Get Started - Create Questions” and verify that the guided generation wizard appears.
        # Get Started - Create Questions button
        elem = page.get_by_role("button", name="Get Started - Create Questions")
        await elem.click(timeout=10000)

        # --> Assertions to verify final state

        # --> The guided generation wizard is open at Step 1, “Choose Exam Section,” with exam-section choices available.
        await (
            page.get_by_role("button", name="Chemistry & Physics Chemical")
            .nth(0)
            .scroll_into_view_if_needed()
        )
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The guided generation wizard displays an exam-section choice.
        (
            await expect(
                page.get_by_role("button", name="Chemistry & Physics Chemical").nth(0)
            ).to_be_visible(timeout=15000),
            "The guided generation wizard displays an exam-section choice.",
        )
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()


asyncio.run(run_test())
