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

        # -> Open the question generator using “Get Started - Create Questions.”
        # Get Started - Create Questions button
        elem = page.get_by_role("button", name="Get Started - Create Questions")
        await elem.click(timeout=10000)

        # -> Continue from the selected Chemistry & Physics section to the unit-selection step.
        # Continue to Unit button
        elem = page.get_by_role("button", name="Continue to Unit")
        await elem.click(timeout=10000)

        # -> Continue to the topic-selection step using the selected chemistry unit.
        # Continue to Topic button
        elem = page.get_by_role("button", name="Continue to Topic")
        await elem.click(timeout=10000)

        # -> Continue from the selected subtopic to the question-level settings.
        # Continue to Level button
        elem = page.get_by_role("button", name="Continue to Level")
        await elem.click(timeout=10000)

        # -> Continue from the level and format settings to the trap-selection step.
        # Continue to Traps button
        elem = page.get_by_role("button", name="Continue to Traps")
        await elem.click(timeout=10000)

        # -> Select the visible “Identify or recognize a scientific concept” subskill and inspect the updated Cognitive Traps screen.
        # Identify or recognize a scientific concept button
        elem = page.get_by_role("button", name="Identify or recognize a")
        await elem.click(timeout=10000)

        # -> Advance from Cognitive Traps to the Visuals step using “Continue to Visuals.”
        # Continue to Visuals button
        elem = page.get_by_role("button", name="Continue to Visuals")
        await elem.click(timeout=10000)

        # -> Open the review screen by selecting “Review Configuration.”
        # Review Configuration button
        elem = page.get_by_role("button", name="Review Configuration")
        await elem.click(timeout=10000)

        # -> Launch the configured batch with “Launch 50-Question Batch” and inspect the generation progress or staged questions.
        # Launch 50-Question Batch button
        elem = page.get_by_role("button", name="Launch 50-Question Batch")
        await elem.click(timeout=10000)

        # -> Open the AI Validated section and inspect whether staged questions can be approved and saved in bulk.
        # AI Validated 150 button
        elem = page.get_by_role("button", name="AI Validated")
        await elem.click(timeout=10000)

        # -> Approve all 150 AI-validated questions using the visible “Approve All Validated (150)” bulk action.
        # Approve All Validated ( 150 ) button
        elem = page.get_by_role("button", name="Approve All Validated (150)")
        await elem.click(timeout=10000)

        # --> Assertions to verify final state

        # --> The AI Validated staging queue is empty.
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The AI Validated staging queue should be empty.
        (
            await expect(page.locator("#root").nth(0)).to_contain_text(
                "No Pending AI Validated Questions", timeout=15000
            ),
            "The AI Validated staging queue should be empty.",
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
