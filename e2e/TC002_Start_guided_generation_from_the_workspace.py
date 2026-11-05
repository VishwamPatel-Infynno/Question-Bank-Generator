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

        # -> Open the question generator using “Get Started - Create Questions” and inspect its configuration fields.
        # Get Started - Create Questions button
        elem = page.get_by_role("button", name="Get Started - Create Questions")
        await elem.click(timeout=10000)

        # -> Continue with the selected Chemistry & Physics section and inspect the available unit choices.
        # Continue to Unit button
        elem = page.get_by_role("button", name="Continue to Unit")
        await elem.click(timeout=10000)

        # -> Continue to the topic step and inspect the available topic choices.
        # Continue to Topic button
        elem = page.get_by_role("button", name="Continue to Topic")
        await elem.click(timeout=10000)

        # -> Continue to the level configuration and inspect the available difficulty choices.
        # Continue to Level button
        elem = page.get_by_role("button", name="Continue to Level")
        await elem.click(timeout=10000)

        # -> Select Independent MCQ as the question format and confirm the selection updates.
        # Independent MCQ Standalone discrete single-choice... button
        elem = page.get_by_role("button", name="Independent MCQ Standalone")
        await elem.click(timeout=10000)

        # -> Choose the “Mini-Batch (5 Questions)” generation mode for a staged run.
        # 🎯 Mini-Batch (5 Questions) button
        elem = page.get_by_role("button", name="🎯 Mini-Batch (5 Questions)")
        await elem.click(timeout=10000)

        # -> Continue from the Level settings to configure the remaining question-generation options.
        # Continue to Traps button
        elem = page.get_by_role("button", name="Continue to Traps")
        await elem.click(timeout=10000)

        # -> Continue from Cognitive Traps & Reasoning Skills to the Visuals configuration step.
        # Continue to Visuals button
        elem = page.get_by_role("button", name="Continue to Visuals")
        await elem.click(timeout=10000)

        # -> Review the configured question-generation settings using “Review Configuration.”
        # Review Configuration button
        elem = page.get_by_role("button", name="Review Configuration")
        await elem.click(timeout=10000)

        # -> Start the configured five-question live generation run using “Generate 5-Question Set (Live)” and verify the pipeline and staged-question status.
        # Generate 5-Question Set (Live) button
        elem = page.get_by_role("button", name="Generate 5-Question Set (Live)")
        await elem.click(timeout=10000)

        # --> Assertions to verify final state

        # --> The live generation pipeline is active.
        await (
            page.locator("xpath=/html/body/div[1]/div/main/div/div[1]/div[1]/div[2]/button[1]")
            .nth(0)
            .scroll_into_view_if_needed()
        )
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The live generation pipeline is active.
        (
            await expect(
                page.locator(
                    "xpath=/html/body/div[1]/div/main/div/div[1]/div[1]/div[2]/button[1]"
                ).nth(0)
            ).to_be_visible(timeout=15000),
            "The live generation pipeline is active.",
        )

        # --> A staged question slot is present while the questions are being prepared.
        await (
            page.get_by_text(
                "Question 1•mediumSingle Choice MCQDirect Question95/100A researcher measures"
            )
            .nth(0)
            .scroll_into_view_if_needed()
        )
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: A staged question slot is present.
        (
            await expect(
                page.get_by_text(
                    "Question 1•mediumSingle Choice MCQDirect Question95/100A researcher measures"
                ).nth(0)
            ).to_be_visible(timeout=15000),
            "A staged question slot is present.",
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
