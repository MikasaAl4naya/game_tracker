import requests
from bs4 import BeautifulSoup

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8",
})

url = "https://keysforgamers.com/ru/buy-pc-games?name=Cyberpunk"
r = session.get(url, timeout=10)
print("Status:", r.status_code)
soup = BeautifulSoup(r.text, "html.parser")

# Look for links containing cyberpunk or games
links = soup.find_all("a")
game_links = []
for a in links:
    href = a.get("href", "")
    text = a.get_text(strip=True)
    if "cyberpunk" in href.lower() or "cyberpunk" in text.lower():
        game_links.append((href, text))

print(f"Cyberpunk matches found: {len(game_links)}")
for href, text in game_links[:10]:
    print(f"  {href} -> {text}")

# Look for price containers
prices = soup.select("[class*='price']")
print(f"Price elements found: {len(prices)}")
for p in prices[:5]:
    print(f"  Class: {p.get('class')} -> Text: {p.get_text(strip=True)}")
