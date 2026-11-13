from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="msedge")
    page = browser.new_page()
    
    requests_log = []
    page.on("request", lambda req: requests_log.append((req.method, req.url)) if ("api" in req.url or "graphql" in req.url or "tariffs" in req.url) and not "yandex" in req.url and not "google" in req.url else None)
    
    page.goto("https://battlepass.ru", wait_until="networkidle")
    
    print("Battlepass network requests:")
    for m, u in requests_log[:20]:
        print(f"  {m} {u}")

    browser.close()
