"""
Screenshot tool for News Llama web mockup
Takes screenshots of all pages for marketing/documentation
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def take_screenshots():
    """Take screenshots of all mockup pages"""
    screenshots_dir = Path("screenshots")
    screenshots_dir.mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2  # Retina/HiDPI
        )
        page = await context.new_page()

        # 1. Home page (profile select)
        print("📸 Taking screenshot: Home page")
        await page.goto("http://localhost:8000/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(
            path=screenshots_dir / "01_home_profile_select.png",
            full_page=True
        )

        # 2. Profile create page
        print("📸 Taking screenshot: Profile create page")
        await page.goto("http://localhost:8000/profile/new")
        await page.wait_for_load_state("networkidle")

        # Select a few interests to show the interaction
        interests = ["AI", "rust", "LocalLLM", "startups", "technology"]
        for interest in interests:
            button = page.locator(f'button:has-text("{interest}")').first
            await button.click()
            await asyncio.sleep(0.1)  # Small delay for visual effect

        await page.screenshot(
            path=screenshots_dir / "02_profile_create_interests.png",
            full_page=True
        )

        # 3. Calendar page
        print("📸 Taking screenshot: Calendar page")
        await page.goto("http://localhost:8000/calendar?user_id=1")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(
            path=screenshots_dir / "03_calendar_view.png",
            full_page=True
        )

        # 4. Profile settings page
        print("📸 Taking screenshot: Profile settings page")
        await page.goto("http://localhost:8000/profile/settings")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(
            path=screenshots_dir / "04_profile_settings.png",
            full_page=True
        )

        # 5. Newsletter modal (if newsletter exists)
        print("📸 Taking screenshot: Newsletter modal")
        await page.goto("http://localhost:8000/calendar?user_id=1")
        await page.wait_for_load_state("networkidle")

        # Click on a day with a newsletter
        newsletter_day = page.locator('.calendar-day.has-newsletter').first
        if await newsletter_day.count() > 0:
            await newsletter_day.click()
            await asyncio.sleep(0.5)  # Wait for modal to open

            # Wait for modal to be visible
            await page.wait_for_selector('#newsletter-modal[style*="flex"]')
            await asyncio.sleep(0.5)  # Wait for iframe to load

            await page.screenshot(
                path=screenshots_dir / "05_newsletter_modal.png",
                full_page=False  # Just viewport, modal should be visible
            )
        else:
            print("⚠️  No newsletter available for modal screenshot")

        await browser.close()

    print(f"\n✅ Screenshots saved to: {screenshots_dir.absolute()}")
    print("\nFiles created:")
    for img in sorted(screenshots_dir.glob("*.png")):
        print(f"  - {img.name}")


if __name__ == "__main__":
    asyncio.run(take_screenshots())
