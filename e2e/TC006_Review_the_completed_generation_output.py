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

        # -> Open the question-generation workflow using “Get Started - Create Questions.”
        # Get Started - Create Questions button
        elem = page.get_by_role("button", name="Get Started - Create Questions")
        await elem.click(timeout=10000)

        # -> Continue from the selected Chemistry & Physics section to the Unit selection step.
        # Continue to Unit button
        elem = page.get_by_role("button", name="Continue to Unit")
        await elem.click(timeout=10000)

        # -> Continue from the selected unit to the Topic selection step.
        # Continue to Topic button
        elem = page.get_by_role("button", name="Continue to Topic")
        await elem.click(timeout=10000)

        # -> Continue from the selected topic and subtopic to the Level selection step.
        # Continue to Level button
        elem = page.get_by_role("button", name="Continue to Level")
        await elem.click(timeout=10000)

        # -> Select “Mini-Batch (5 Questions)” to use the staged batch desk for reviewing generated questions.
        # 🎯 Mini-Batch (5 Questions) button
        elem = page.get_by_role("button", name="🎯 Mini-Batch (5 Questions)")
        await elem.click(timeout=10000)

        # -> Continue from the Level and Format step to the Traps step.
        # Continue to Traps button
        elem = page.get_by_role("button", name="Continue to Traps")
        await elem.click(timeout=10000)

        # -> Continue from the Cognitive Traps & Reasoning Skills step to Visuals.
        # Continue to Visuals button
        elem = page.get_by_role("button", name="Continue to Visuals")
        await elem.click(timeout=10000)

        # -> Open the review step by selecting “Review Configuration.”
        # Review Configuration button
        elem = page.get_by_role("button", name="Review Configuration")
        await elem.click(timeout=10000)

        # -> Click “Generate 5-Question Set (Live)” and verify the staged questions and generation-complete status.
        # Generate 5-Question Set (Live) button
        elem = page.get_by_role("button", name="Generate 5-Question Set (Live)")
        await elem.click(timeout=10000)

        # --> Assertions to verify final state

        # --> Five staged questions are available for review.
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The review area shows five generated questions.
        (
            await expect(page.get_by_role("main").nth(0)).to_contain_text(
                "5 Generated", timeout=15000
            ),
            "The review area shows five generated questions.",
        )
        await (
            page.get_by_text(
                "Question 1•mediumSingle Choice MCQPassage Set95/100References shared reading"
            )
            .nth(0)
            .scroll_into_view_if_needed()
        )
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: A staged question is visible for review.
        (
            await expect(
                page.get_by_text(
                    "Question 1•mediumSingle Choice MCQPassage Set95/100References shared reading"
                ).nth(0)
            ).to_be_visible(timeout=15000),
            "A staged question is visible for review.",
        )

        # --> Generation is complete, with all five questions ready.
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The generation status shows that all five questions are ready.
        (
            await expect(page.get_by_role("main").nth(0)).to_contain_text(
                "All Questions Ready (5 Questions Created)", timeout=15000
            ),
            "The generation status shows that all five questions are ready.",
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
