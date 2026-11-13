import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        await page.goto("http://localhost:8080/topup", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Click Q6
        q6_btn = page.locator("button:has-text('Какие действуют лимиты на пополнение баланса Steam?')")
        await q6_btn.scroll_into_view_if_needed()
        await q6_btn.click()
        await page.wait_for_timeout(300)

        # Click Q7
        q7_btn = page.locator("button:has-text('Почему новый аккаунт может сменить регион на Узбекистан/USD')")
        await q7_btn.click()
        await page.wait_for_timeout(300)

        # Click Q8
        q8_btn = page.locator("button:has-text('Жителям Крыма, ДНР, ЛНР и Севастополя')")
        await q8_btn.click()
        await page.wait_for_timeout(300)

        await page.screenshot(path="faq_expanded_preview.png")
        print("Captured faq_expanded_preview.png with Q6, Q7, Q8 open")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
