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

        # -> Open the question creation workspace using “Get Started - Create Questions.”
        # Get Started - Create Questions button
        elem = page.get_by_role("button", name="Get Started - Create Questions")
        await elem.click(timeout=10000)

        # -> Select the Chemistry & Physics section to continue setting up a question generation run.
        # Chemistry & Physics Chemical and Physical... button
        elem = page.get_by_role("button", name="Chemistry & Physics Chemical")
        await elem.click(timeout=10000)

        # -> Continue to the topic-selection step using the visible “Continue to Topic” control.
        # Continue to Topic button
        elem = page.get_by_role("button", name="Continue to Topic")
        await elem.click(timeout=10000)

        # -> Select a target subtopic concept and continue to the difficulty-level settings.
        # Isotopes and average atomic mass button
        elem = page.get_by_role("button", name="Isotopes and average atomic")
        await elem.click(timeout=10000)

        # -> Continue to the difficulty settings using “Continue to Level.”
        # Continue to Level button
        elem = page.get_by_role("button", name="Continue to Level")
        await elem.click(timeout=10000)

        # -> Choose the Independent MCQ format before proceeding with the generation setup.
        # Independent MCQ Standalone discrete single-choice... button
        elem = page.get_by_role("button", name="Independent MCQ Standalone")
        await elem.click(timeout=10000)

        # -> Choose “Mini-Batch (5 Questions)” to configure batch generation.
        # 🎯 Mini-Batch (5 Questions) button
        elem = page.get_by_role("button", name="🎯 Mini-Batch (5 Questions)")
        await elem.click(timeout=10000)

        # -> Continue to the trap-settings screen using “Continue to Traps.”
        # Continue to Traps button
        elem = page.get_by_role("button", name="Continue to Traps")
        await elem.click(timeout=10000)

        # -> Continue from Cognitive Traps & Reasoning Skills to the Visuals setup.
        # Continue to Visuals button
        elem = page.get_by_role("button", name="Continue to Visuals")
        await elem.click(timeout=10000)

        # -> Open the configuration review screen using “Review Configuration.”
        # Review Configuration button
        elem = page.get_by_role("button", name="Review Configuration")
        await elem.click(timeout=10000)

        # -> Start the live single-question generation using “Generate Single Question (Live)” and inspect the active pipeline controls.
        # Generate Single Question (Live) button
        elem = page.get_by_role("button", name="Generate Single Question (")
        await elem.click(timeout=10000)

        # --> Assertions to verify final state

        # --> The generation run ended and its question is ready for review.
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The generation result should be ready for review after the run stops.
        (
            await expect(page.get_by_role("main").nth(0)).to_contain_text(
                "Ready for Review", timeout=15000
            ),
            "The generation result should be ready for review after the run stops.",
        )

        # --> The workspace displays an idle status after generation stops.
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The workspace should display an idle status.
        (
            await expect(page.get_by_role("main").nth(0)).to_contain_text("Idle", timeout=15000),
            "The workspace should display an idle status.",
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
