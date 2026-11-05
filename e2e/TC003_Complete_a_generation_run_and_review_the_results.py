import asyncio
import contextlib
import os

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
        await page.goto(os.environ.get("E2E_BASE_URL", "http://localhost:5173/"))
        with contextlib.suppress(Exception):
            await page.wait_for_load_state("domcontentloaded", timeout=5000)

        # -> Open the question generator using “Get Started - Create Questions.”
        # Get Started - Create Questions button
        elem = page.get_by_role("button", name="Get Started - Create Questions")
        await elem.click(timeout=10000)

        # -> Continue from the selected Chemistry & Physics section to choose a unit.
        # Continue to Unit button
        elem = page.get_by_role("button", name="Continue to Unit")
        await elem.click(timeout=10000)

        # -> Continue to the topic-selection step using “Continue to Topic.”
        # Continue to Topic button
        elem = page.get_by_role("button", name="Continue to Topic")
        await elem.click(timeout=10000)

        # -> Continue from the selected topic to the level step and inspect the available difficulty options.
        # Continue to Level button
        elem = page.get_by_role("button", name="Continue to Level")
        await elem.click(timeout=10000)

        # -> Choose a challenge level and question format, then continue to the traps step.
        # 99th Percentile Elite (~518-528 MCAT) Subtle data... button
        elem = page.get_by_role("button", name="99th Percentile Elite (~518-")
        await elem.click(timeout=10000)

        # -> Choose a challenge level and question format, then continue to the traps step.
        # Independent MCQ Standalone discrete single-choice... button
        elem = page.get_by_role("button", name="Independent MCQ Standalone")
        await elem.click(timeout=10000)

        # -> Continue to the traps step and inspect the available settings.
        # Continue to Traps button
        elem = page.get_by_role("button", name="Continue to Traps")
        await elem.click(timeout=10000)

        # -> Continue from Cognitive Traps & Reasoning Skills to the Visuals step.
        # Continue to Visuals button
        elem = page.get_by_role("button", name="Continue to Visuals")
        await elem.click(timeout=10000)

        # -> Open the configuration review using “Review Configuration” and inspect the final generation controls.
        # Review Configuration button
        elem = page.get_by_role("button", name="Review Configuration")
        await elem.click(timeout=10000)

        # -> Click “Launch 50-Question Batch” to start generation.
        # Launch 50-Question Batch button
        elem = page.get_by_role("button", name="Launch 50-Question Batch")
        await elem.click(timeout=10000)

        # -> Refresh the batch activity list and check whether the newest 50-question run has completed.
        # Refresh button
        elem = page.get_by_role("button", name="Refresh")
        await elem.click(timeout=10000)

        # -> Open the completed “Protons, neutrons, and electrons” batch to verify generated question text is visible.
        # Chemical and Physical Foundations medium Passage...
        elem = page.locator("div:nth-child(4) > div > div").first
        await elem.click(timeout=10000)

        # -> Open a completed job’s “View 5 Generated Questions” panel and verify that generated question text is visible.
        # View 5 Generated Questions button
        elem = page.locator("div:nth-child(4) > .btn-secondary").first
        await elem.click(timeout=10000)

        # --> Assertions to verify final state

        # --> The generated batch is marked completed.
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The batch should be marked Completed.
        (
            await expect(
                page.locator(
                    "xpath=/html/body/div[1]/div/main/div/div[4]/div[1]/div[1]/div[3]/span"
                ).nth(0)
            ).to_have_text("Completed", timeout=15000),
            "The batch should be marked Completed.",
        )

        # --> Generated questions are available in the expanded job panel.
        await (
            page.get_by_role("button", name="Hide 5 Generated Questions")
            .nth(0)
            .scroll_into_view_if_needed()
        )
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The generated-question panel should be expanded.
        (
            await expect(
                page.get_by_role("button", name="Hide 5 Generated Questions").nth(0)
            ).to_be_visible(timeout=15000),
            "The generated-question panel should be expanded.",
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
