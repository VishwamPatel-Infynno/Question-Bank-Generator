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

        # -> Open the Question Generator view from the main navigation.
        # Question Generator button
        elem = page.get_by_role("button", name="Question Generator")
        await elem.click(timeout=10000)

        # -> Open the Batch Activity view from the main navigation.
        # Batch Activity 2 button
        elem = page.get_by_role("button", name="Batch Activity")
        await elem.click(timeout=10000)

        # -> Open the AI Validated view from the main navigation.
        # AI Validated button
        elem = page.get_by_role("button", name="AI Validated")
        await elem.click(timeout=10000)

        # -> Open the Question Bank view from the main navigation and verify its repository is displayed.
        # Question Bank button
        elem = page.get_by_role("button", name="Question Bank", exact=True)
        await elem.click(timeout=10000)

        # --> Assertions to verify final state

        # --> The Question Bank repository is displayed with visible question cards.
        await (
            page.locator("div:nth-child(3) > div > div > div:nth-child(2) > button")
            .first.nth(0)
            .scroll_into_view_if_needed()
        )
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The Question Bank repository should display a question card.
        (
            await expect(
                page.locator("div:nth-child(3) > div > div > div:nth-child(2) > button").first.nth(
                    0
                )
            ).to_be_visible(timeout=15000),
            "The Question Bank repository should display a question card.",
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
