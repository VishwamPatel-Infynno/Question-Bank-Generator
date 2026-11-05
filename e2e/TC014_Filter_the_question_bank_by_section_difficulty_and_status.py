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

        # -> Open the question repository using the visible 'Browse Question Bank' button.
        # Browse Question Bank button
        elem = page.get_by_role("button", name="Browse Question Bank")
        await elem.click(timeout=10000)

        # -> Filter the question bank to the Chem / Phys section and inspect the resulting list.
        # Chem / Phys button
        elem = page.get_by_role("button", name="Chem / Phys")
        await elem.click(timeout=10000)

        # -> Select the “Medium” difficulty filter and check that the question list reflects that choice.
        # Medium button
        elem = page.get_by_role("button", name="Medium")
        await elem.click(timeout=10000)

        # -> Select the “Approved” status filter and verify the resulting question list matches all three selected filters.
        # Approved button
        elem = page.get_by_role("button", name="Approved")
        await elem.click(timeout=10000)

        # --> Assertions to verify final state

        # --> The displayed results are narrowed to Chem / Phys questions at Medium difficulty with Approved status.
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: Verify the displayed question matches the selected section, difficulty, and status filters.
        (
            await expect(page.locator("#root").nth(0)).to_contain_text(
                "Chemical and Physical Foundations of Biological Systems \u2022 Protons, neutrons, and electrons \u2022 medium 95 /100 MCAT 129 Skill 2 Approved",
                timeout=15000,
            ),
            "Verify the displayed question matches the selected section, difficulty, and status filters.",
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
