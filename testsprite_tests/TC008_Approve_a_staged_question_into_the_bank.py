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

        # -> Open the question creation flow using “Get Started - Create Questions” and inspect the generator form.
        # Get Started - Create Questions button
        elem = page.get_by_role("button", name="Get Started - Create Questions")
        await elem.click(timeout=10000)

        # -> Continue from “Choose Exam Section” to the Unit selection step.
        # Continue to Unit button
        elem = page.get_by_role("button", name="Continue to Unit")
        await elem.click(timeout=10000)

        # -> Continue to the topic-selection step and inspect the available topic controls.
        # Continue to Topic button
        elem = page.get_by_role("button", name="Continue to Topic")
        await elem.click(timeout=10000)

        # -> Continue from topic selection to the level step and inspect its controls.
        # Continue to Level button
        elem = page.get_by_role("button", name="Continue to Level")
        await elem.click(timeout=10000)

        # -> Set the generation scope to “Mini-Batch (5 Questions)” and inspect the updated generator state.
        # 🎯 Mini-Batch (5 Questions) button
        elem = page.get_by_role("button", name="🎯 Mini-Batch (5 Questions)")
        await elem.click(timeout=10000)

        # -> Continue from the Level & Format step to the Traps step.
        # Continue to Traps button
        elem = page.get_by_role("button", name="Continue to Traps")
        await elem.click(timeout=10000)

        # -> Continue from Cognitive Traps & Reasoning Skills to the Visuals step.
        # Continue to Visuals button
        elem = page.get_by_role("button", name="Continue to Visuals")
        await elem.click(timeout=10000)

        # -> Open the configuration review using “Review Configuration.”
        # Review Configuration button
        elem = page.get_by_role("button", name="Review Configuration")
        await elem.click(timeout=10000)

        # -> Generate one MCAT question using “Generate Single Question (Live)” and inspect the resulting question state.
        # Generate Single Question (Live) button
        elem = page.get_by_role("button", name="Generate Single Question (")
        await elem.click(timeout=10000)

        # -> Scroll down through the staged question to locate its approval and save controls.
        await page.mouse.wheel(0, 300)

        # -> Approve the staged question with “Save to Question Bank” and check the resulting confirmation.
        # Save to Question Bank A button
        elem = page.get_by_role("button", name="Save to Question Bank A")
        await elem.click(timeout=10000)

        # --> Assertions to verify final state

        # --> The approved question is shown as saved in the question bank rather than awaiting review.
        # Assert-outcome: not verified — the export-time check could not be evaluated
        # Assert: The approved question is shown as saved in the question bank.
        (
            await expect(page.get_by_role("main").nth(0)).to_contain_text(
                "Saved in Bank", timeout=15000
            ),
            "The approved question is shown as saved in the question bank.",
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
