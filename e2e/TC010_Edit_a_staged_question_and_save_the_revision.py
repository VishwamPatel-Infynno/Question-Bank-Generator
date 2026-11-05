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

        # -> Open the question creation workflow by selecting “Get Started - Create Questions.”
        # Get Started - Create Questions button
        elem = page.get_by_role("button", name="Get Started - Create Questions")
        await elem.click(timeout=10000)

        # -> Continue from the selected Chemistry & Physics section to choose the unit.
        # Continue to Unit button
        elem = page.get_by_role("button", name="Continue to Unit")
        await elem.click(timeout=10000)

        # -> Continue with the selected General Chemistry unit to choose a topic.
        # Continue to Topic button
        elem = page.get_by_role("button", name="Continue to Topic")
        await elem.click(timeout=10000)

        # -> Continue from the selected Atomic Structure concept to choose the question level.
        # Continue to Level button
        elem = page.get_by_role("button", name="Continue to Level")
        await elem.click(timeout=10000)

        # -> Choose Independent MCQ as the question format.
        # Independent MCQ Standalone discrete single-choice... button
        elem = page.get_by_role("button", name="Independent MCQ Standalone")
        await elem.click(timeout=10000)

        # -> Select the “Mini-Batch (5 Questions)” batch desk option.
        # 🎯 Mini-Batch (5 Questions) button
        elem = page.get_by_role("button", name="🎯 Mini-Batch (5 Questions)")
        await elem.click(timeout=10000)

        # -> Continue to the traps configuration using the visible “Continue to Traps” button.
        # Continue to Traps button
        elem = page.get_by_role("button", name="Continue to Traps")
        await elem.click(timeout=10000)

        # -> Continue from the cognitive-traps setup to the visual configuration screen.
        # Continue to Visuals button
        elem = page.get_by_role("button", name="Continue to Visuals")
        await elem.click(timeout=10000)

        # -> Open the configuration review using “Review Configuration.”
        # Review Configuration button
        elem = page.get_by_role("button", name="Review Configuration")
        await elem.click(timeout=10000)

        # -> Start generating the staged five-question set using “Generate 5-Question Set (Live).”
        # Generate 5-Question Set (Live) button
        elem = page.get_by_role("button", name="Generate 5-Question Set (Live)")
        await elem.click(timeout=10000)

        # -> Open the first generated question’s detailed view to find its editing controls.
        # Detailed View button
        elem = page.locator("div:nth-child(5) > button").first
        await elem.click(timeout=10000)

        # -> Open the first question’s “Quick Edit” form to inspect its editable fields.
        # Quick Edit E button
        elem = page.get_by_role("button", name="Quick Edit E")
        await elem.click(timeout=10000)

        # -> Append a short revision marker to the first staged question’s text in Quick Edit Mode.
        # A researcher measures the rate of an enzymatic... text area
        elem = page.get_by_text("[Revised for review]A")
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill(" [Revised for review]")

        # -> Save the edited staged question and confirm the updated text remains available for review.
        # Save button
        elem = page.get_by_role("button", name="Save", exact=True)
        await elem.click(timeout=10000)

        # --> Assertions to verify final state

        # --> The saved question retains the revision marker “[Revised for review].”
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The saved question should retain the revision marker.
        (
            await expect(page.get_by_role("main").nth(0)).to_contain_text(
                "[Revised for review]", timeout=15000
            ),
            "The saved question should retain the revision marker.",
        )

        # --> The revised staged question remains ready for review.
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The staged question should remain marked Ready for Review.
        (
            await expect(page.get_by_role("main").nth(0)).to_contain_text(
                "Ready for Review", timeout=15000
            ),
            "The staged question should remain marked Ready for Review.",
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
