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

        # -> Continue from the selected exam section to choose the question’s unit.
        # Continue to Unit button
        elem = page.get_by_role("button", name="Continue to Unit")
        await elem.click(timeout=10000)

        # -> Continue to topic selection using the visible “Continue to Topic” control.
        # Continue to Topic button
        elem = page.get_by_role("button", name="Continue to Topic")
        await elem.click(timeout=10000)

        # -> Continue from the selected topic and concept to the question-level settings.
        # Continue to Level button
        elem = page.get_by_role("button", name="Continue to Level")
        await elem.click(timeout=10000)

        # -> Choose Independent MCQ and Mini-Batch (5 Questions) so the workflow produces questions on the batch desk.
        # Independent MCQ Standalone discrete single-choice... button
        elem = page.get_by_role("button", name="Independent MCQ Standalone")
        await elem.click(timeout=10000)

        # -> Choose Independent MCQ and Mini-Batch (5 Questions) so the workflow produces questions on the batch desk.
        # 🎯 Mini-Batch (5 Questions) button
        elem = page.get_by_role("button", name="🎯 Mini-Batch (5 Questions)")
        await elem.click(timeout=10000)

        # -> Continue from the calibration screen to the trap-selection step.
        # Continue to Traps button
        elem = page.get_by_role("button", name="Continue to Traps")
        await elem.click(timeout=10000)

        # -> Continue from Cognitive Traps & Reasoning Skills to the Visuals step.
        # Continue to Visuals button
        elem = page.get_by_role("button", name="Continue to Visuals")
        await elem.click(timeout=10000)

        # -> Review the question-generation configuration using the visible “Review Configuration” control.
        # Review Configuration button
        elem = page.get_by_role("button", name="Review Configuration")
        await elem.click(timeout=10000)

        # -> Start generating the configured 5-question set using “Generate 5-Question Set (Live).”
        # Generate 5-Question Set (Live) button
        elem = page.get_by_role("button", name="Generate 5-Question Set (Live)")
        await elem.click(timeout=10000)

        # -> Open “Detailed View” for the first generated question to reveal its full content.
        # Detailed View button
        elem = page.locator("div:nth-child(5) > button").first
        await elem.click(timeout=10000)

        # -> Open the “AI Creation Steps” tab to review the generated question’s audit reasoning.
        # AI Creation Steps button
        elem = page.get_by_role("button", name="AI Creation Steps")
        await elem.click(timeout=10000)

        # --> Assertions to verify final state

        # --> The generated question’s full details are visible.
        await (
            page.locator("div:nth-child(2) > div:nth-child(3)")
            .first.nth(0)
            .scroll_into_view_if_needed()
        )
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The expanded generated question details are visible.
        (
            await expect(
                page.locator("div:nth-child(2) > div:nth-child(3)").first.nth(0)
            ).to_be_visible(timeout=15000),
            "The expanded generated question details are visible.",
        )

        # --> The AI Creation Steps audit view displays the question’s stage payload.
        await (
            page.get_by_role("main")
            .locator("div")
            .filter(has_text="Stage Outcome JSON Inspector(")
            .nth(4)
            .nth(0)
            .scroll_into_view_if_needed()
        )
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The AI Creation Steps audit payload is visible.
        (
            await expect(
                page.get_by_role("main")
                .locator("div")
                .filter(has_text="Stage Outcome JSON Inspector(")
                .nth(4)
                .nth(0)
            ).to_be_visible(timeout=15000),
            "The AI Creation Steps audit payload is visible.",
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
