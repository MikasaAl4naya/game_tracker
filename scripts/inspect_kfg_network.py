from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="msedge")
    page = browser.new_page()
    
    requests_log = []
    page.on("request", lambda req: requests_log.append((req.method, req.url)) if "api" in req.url or "search" in req.url or "products" in req.url or "graphql" in req.url else None)
    
    page.goto("https://keysforgamers.com/ru", wait_until="networkidle")
    
    # Try searching
    search_input = page.locator("input[name='name']")
    if search_input.count() > 0:
        search_input.fill("Cyberpunk")
        page.keyboard.press("Enter")
        page.wait_for_timeout(3000)

    print("Logged API/Search network requests:")
    for m, u in requests_log[:20]:
        print(f"  {m} {u}")

    browser.close()
