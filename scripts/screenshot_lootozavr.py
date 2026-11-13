import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        await page.goto("http://localhost:8080/", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="lootozavr_home_preview.png")
        print("Captured lootozavr_home_preview.png")

        # Open tracking modal
        first_track_btn = page.locator(".track-btn").first
        if await first_track_btn.is_visible():
            await first_track_btn.click()
            await page.wait_for_timeout(500)
            await page.screenshot(path="lootozavr_modal_preview.png")
            print("Captured lootozavr_modal_preview.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
