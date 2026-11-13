import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        await page.goto("http://localhost:8080/topup", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        
        # Take full screenshot
        await page.screenshot(path="topup_page_preview.png", full_page=False)
        print("Captured topup_page_preview.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
