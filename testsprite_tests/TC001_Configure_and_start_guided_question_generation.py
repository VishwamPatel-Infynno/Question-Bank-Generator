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

        # -> Click “Get Started - Create Questions” to open the guided question setup.
        # Get Started - Create Questions button
        elem = page.get_by_role("button", name="Get Started - Create Questions")
        await elem.click(timeout=10000)

        # -> Continue from the selected Chemistry & Physics exam section to the unit selection step.
        # Continue to Unit button
        elem = page.get_by_role("button", name="Continue to Unit")
        await elem.click(timeout=10000)

        # -> Continue from the selected chemistry unit to the topic selection step.
        # Continue to Topic button
        elem = page.get_by_role("button", name="Continue to Topic")
        await elem.click(timeout=10000)

        # -> Select “Electron configurations” as the target concept and continue to the difficulty-level step.
        # Electron configurations button
        elem = page.get_by_role("button", name="Electron configurations")
        await elem.click(timeout=10000)

        # -> Select “Electron configurations” as the target concept and continue to the difficulty-level step.
        # Continue to Level button
        elem = page.get_by_role("button", name="Continue to Level")
        await elem.click(timeout=10000)

        # -> Select the visible “Independent MCQ” question format and review the updated configuration.
        # Independent MCQ Standalone discrete single-choice... button
        elem = page.get_by_role("button", name="Independent MCQ Standalone")
        await elem.click(timeout=10000)

        # -> Choose “Mini-Batch (5 Questions)” to configure batch generation, then continue to the traps step.
        # 🎯 Mini-Batch (5 Questions) button
        elem = page.get_by_role("button", name="🎯 Mini-Batch (5 Questions)")
        await elem.click(timeout=10000)

        # -> Continue from the selected live generation configuration to the traps setup.
        # Continue to Traps button
        elem = page.get_by_role("button", name="Continue to Traps")
        await elem.click(timeout=10000)

        # -> Open the Visuals step using “Continue to Visuals” and inspect the available AI diagram or image generation option.
        # Continue to Visuals button
        elem = page.get_by_role("button", name="Continue to Visuals")
        await elem.click(timeout=10000)

        # -> Enable AI-generated visuals when pedagogically needed for the configured question.
        # When Needed button
        elem = page.get_by_role("button", name="When Needed")
        await elem.click(timeout=10000)

        # -> Click “Review Configuration” to inspect the completed setup before launching question generation.
        # Review Configuration button
        elem = page.get_by_role("button", name="Review Configuration")
        await elem.click(timeout=10000)

        # -> Click “Generate Single Question (Live)” to launch generation and verify the live pipeline and its progress information.
        # Generate Single Question (Live) button
        elem = page.get_by_role("button", name="Generate Single Question (")
        await elem.click(timeout=10000)

        # --> Assertions to verify final state

        # --> The live generation pipeline is displayed.
        await (
            page.locator("#root div")
            .filter(has_text="Ready for Review|Chemical and")
            .nth(2)
            .nth(0)
            .scroll_into_view_if_needed()
        )
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The live generation pipeline is visible.
        (
            await expect(
                page.locator("#root div")
                .filter(has_text="Ready for Review|Chemical and")
                .nth(2)
                .nth(0)
            ).to_be_visible(timeout=15000),
            "The live generation pipeline is visible.",
        )

        # --> Generation progress information is displayed.
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: Generation progress information is displayed.
        (
            await expect(page.locator("#root").nth(0)).to_contain_text(
                "Generation Started", timeout=15000
            ),
            "Generation progress information is displayed.",
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
