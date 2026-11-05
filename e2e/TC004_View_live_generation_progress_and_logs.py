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

        # -> Open the question creation flow using “Get Started - Create Questions.”
        # Get Started - Create Questions button
        elem = page.get_by_role("button", name="Get Started - Create Questions")
        await elem.click(timeout=10000)

        # -> Continue from the selected Chemistry & Physics section to the Unit selection step.
        # Continue to Unit button
        elem = page.get_by_role("button", name="Continue to Unit")
        await elem.click(timeout=10000)

        # -> Continue to the topic-selection step using the visible “Continue to Topic” button.
        # Continue to Topic button
        elem = page.get_by_role("button", name="Continue to Topic")
        await elem.click(timeout=10000)

        # -> Continue from the selected topic and subtopic to the Level step.
        # Continue to Level button
        elem = page.get_by_role("button", name="Continue to Level")
        await elem.click(timeout=10000)

        # -> Select the visible Foundational difficulty option before continuing the generator setup.
        # Foundational (~500 MCAT) Direct clues and... button
        elem = page.get_by_role("button", name="Foundational (~500 MCAT)")
        await elem.click(timeout=10000)

        # -> Select “Mini-Batch (5 Questions)” to enable the generation workspace and telemetry.
        # 🎯 Mini-Batch (5 Questions) button
        elem = page.get_by_role("button", name="🎯 Mini-Batch (5 Questions)")
        await elem.click(timeout=10000)

        # -> Continue to the Traps step using the visible “Continue to Traps” button.
        # Continue to Traps button
        elem = page.get_by_role("button", name="Continue to Traps")
        await elem.click(timeout=10000)

        # -> Continue from Cognitive Traps & Reasoning Skills to the Visuals step using “Continue to Visuals.”
        # Continue to Visuals button
        elem = page.get_by_role("button", name="Continue to Visuals")
        await elem.click(timeout=10000)

        # -> Open the configuration review using “Review Configuration.”
        # Review Configuration button
        elem = page.get_by_role("button", name="Review Configuration")
        await elem.click(timeout=10000)

        # -> Start live question generation using “Generate Single Question (Live)” and inspect the resulting pipeline status.
        # Generate Single Question (Live) button
        elem = page.get_by_role("button", name="Generate Single Question (")
        await elem.click(timeout=10000)

        # -> Return to the generation status and Logs control to verify whether live telemetry and event entries are visible.
        await page.mouse.wheel(0, 300)

        # -> Open the visible “Logs” panel and verify whether it displays event entries and live pipeline telemetry.
        # Logs button
        elem = page.get_by_role("button", name="Logs")
        await elem.click(timeout=10000)

        # --> Assertions to verify final state

        # --> The live pipeline event stream is displayed.
        await (
            page.get_by_text(
                "Live Agent Event Stream & Processing Stage Logs (13 events)[Passage Writer]"
            )
            .nth(0)
            .scroll_into_view_if_needed()
        )
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The live pipeline event stream is visible.
        (
            await expect(
                page.get_by_text(
                    "Live Agent Event Stream & Processing Stage Logs (13 events)[Passage Writer]"
                ).nth(0)
            ).to_be_visible(timeout=15000),
            "The live pipeline event stream is visible.",
        )

        # --> The active agent stage is visible during processing.
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The active agent stage is shown in the generation status.
        (
            await expect(page.get_by_role("main").nth(0)).to_contain_text(
                "Question Writer & Reviewer", timeout=15000
            ),
            "The active agent stage is shown in the generation status.",
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
