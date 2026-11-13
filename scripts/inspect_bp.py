import requests

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

try:
    r = session.get("https://battlepass.ru", timeout=5)
    print("Battlepass status:", r.status_code, "Length:", len(r.text))
except Exception as e:
    print("Battlepass error:", e)
