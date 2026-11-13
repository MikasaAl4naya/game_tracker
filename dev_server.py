"""
LootoZavr Design & Frontend Development Server (Standalone / No Docker).
Не требует Docker, PostgreSQL, Redis или сторонних библиотек.
Запуск:
    python dev_server.py
Открывает http://localhost:8080 с полными моковыми данными для верстки и дизайна.
"""
import http.server
import json
import os
import re
import socketserver
import sys
from urllib.parse import parse_qs, urlparse

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "index.html")

# ─── Mock Data for Designer ────────────────────────────────────────────────
MOCK_GAMES = [
    {
        "id": 1,
        "name": "Cyberpunk 2077",
        "steam_appid": 1091500,
        "current_min_price": 53.0,
        "base_price": 2499.0,
        "discount_percent": 98,
        "is_free": False,
        "owners": "20,000,000 .. 50,000,000",
        "image_url": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/1091500/header.jpg"
    },
    {
        "id": 2,
        "name": "ELDEN RING",
        "steam_appid": 1245620,
        "current_min_price": 51.0,
        "base_price": 3599.0,
        "discount_percent": 98,
        "is_free": False,
        "owners": "20,000,000 .. 50,000,000",
        "image_url": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/1245620/header.jpg"
    },
    {
        "id": 3,
        "name": "Hogwarts Legacy",
        "steam_appid": 990080,
        "current_min_price": 71.0,
        "base_price": 2999.0,
        "discount_percent": 97,
        "is_free": False,
        "owners": "10,000,000 .. 20,000,000",
        "image_url": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/990080/header.jpg"
    },
    {
        "id": 4,
        "name": "Palworld",
        "steam_appid": 1623730,
        "current_min_price": 164.0,
        "base_price": 1500.0,
        "discount_percent": 89,
        "is_free": False,
        "owners": "20,000,000 .. 50,000,000",
        "image_url": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/1623730/header.jpg"
    },
    {
        "id": 5,
        "name": "Black Myth: Wukong",
        "steam_appid": 2358720,
        "current_min_price": 52.0,
        "base_price": 3599.0,
        "discount_percent": 98,
        "is_free": False,
        "owners": "20,000,000 .. 50,000,000",
        "image_url": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/2358720/header.jpg"
    },
    {
        "id": 6,
        "name": "Monster Hunter Wilds",
        "steam_appid": 2246340,
        "current_min_price": 65.0,
        "base_price": 4999.0,
        "discount_percent": 98,
        "is_free": False,
        "owners": "2,000,000 .. 5,000,000",
        "image_url": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/2246340/header.jpg"
    },
    {
        "id": 7,
        "name": "ARK: Survival Evolved",
        "steam_appid": 346110,
        "current_min_price": 75.0,
        "base_price": 1050.0,
        "discount_percent": 92,
        "is_free": False,
        "owners": "10,000,000 .. 20,000,000",
        "image_url": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/346110/header.jpg"
    },
    {
        "id": 8,
        "name": "DayZ",
        "steam_appid": 221100,
        "current_min_price": 89.0,
        "base_price": 2790.0,
        "discount_percent": 96,
        "is_free": False,
        "owners": "10,000,000 .. 20,000,000",
        "image_url": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/221100/header.jpg"
    },
    {
        "id": 9,
        "name": "Terraria",
        "steam_appid": 105600,
        "current_min_price": 109.0,
        "base_price": 385.0,
        "discount_percent": 71,
        "is_free": False,
        "owners": "20,000,000 .. 50,000,000",
        "image_url": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/105600/header.jpg"
    },
    {
        "id": 10,
        "name": "Among Us",
        "steam_appid": 945360,
        "current_min_price": 120.0,
        "base_price": 350.0,
        "discount_percent": 65,
        "is_free": False,
        "owners": "20,000,000 .. 50,000,000",
        "image_url": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/945360/header.jpg"
    },
    {
        "id": 11,
        "name": "Grand Theft Auto V",
        "steam_appid": 271590,
        "current_min_price": 450.0,
        "base_price": 1500.0,
        "discount_percent": 70,
        "is_free": False,
        "owners": "50,000,000 .. 100,000,000",
        "image_url": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/271590/header.jpg"
    },
    {
        "id": 12,
        "name": "Baldur's Gate 3",
        "steam_appid": 1086940,
        "current_min_price": 1799.0,
        "base_price": 1999.0,
        "discount_percent": 10,
        "is_free": False,
        "owners": "20,000,000 .. 50,000,000",
        "image_url": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/1086940/header.jpg"
    }
]

MOCK_DONATE_GAMES = [
    {
        "slug": "genshin-impact",
        "name": "Genshin Impact",
        "publisher": "HoYoverse",
        "icon": "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?auto=format&fit=crop&w=120&q=80",
        "banner": "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "Кристаллы сотворения",
        "id_type": "UID + Сервер",
        "min_price": 95,
        "badge": "🔥 Топ доната"
    },
    {
        "slug": "brawl-stars",
        "name": "Brawl Stars",
        "publisher": "Supercell",
        "icon": "https://images.unsplash.com/photo-1563089145-599997674d42?auto=format&fit=crop&w=120&q=80",
        "banner": "https://images.unsplash.com/photo-1563089145-599997674d42?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "Гемы",
        "id_type": "Player Tag (#)",
        "min_price": 115,
        "badge": "⚡ Хит"
    },
    {
        "slug": "roblox",
        "name": "Roblox",
        "publisher": "Roblox Corp",
        "icon": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=120&q=80",
        "banner": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "Робуксы",
        "id_type": "Username (Логин)",
        "min_price": 89,
        "badge": "🎮 Популярно"
    },
    {
        "slug": "honkai-star-rail",
        "name": "Honkai: Star Rail",
        "publisher": "HoYoverse",
        "icon": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=120&q=80",
        "banner": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "Сущности древних снов",
        "id_type": "UID + Сервер",
        "min_price": 99,
        "badge": "⭐ Хит"
    }
]

MOCK_PACKAGES_GENSHIN = [
    {
        "id": "genshin-blessing",
        "name": "Благословение полой луны",
        "category": "subscription",
        "amount_text": "30 дней (3000 камней)",
        "icon": "fa-solid fa-moon",
        "accent_color": "#FBBF24",
        "prices": [
            { "shop_name": "Donatov.net", "price": 429, "rating": "4.9", "url": "https://donatov.net", "methods": ["sbp", "card"] },
            { "shop_name": "Kupikod", "price": 449, "rating": "4.8", "url": "https://kupikod.com", "methods": ["sbp", "card"] },
            { "shop_name": "PlayerOK", "price": 435, "rating": "4.7", "url": "https://playerok.com", "methods": ["sbp", "crypto"] },
            { "shop_name": "FunPay", "price": 419, "rating": "4.9", "url": "https://funpay.com", "methods": ["sbp", "card"] }
        ]
    },
    {
        "id": "genshin-300",
        "name": "300 + 30 Кристаллов",
        "category": "currency",
        "amount_text": "330 кристаллов",
        "icon": "fa-solid fa-gem",
        "accent_color": "#38BDF8",
        "prices": [
            { "shop_name": "Donatov.net", "price": 420, "rating": "4.9", "url": "https://donatov.net", "methods": ["sbp", "card"] },
            { "shop_name": "Kupikod", "price": 439, "rating": "4.8", "url": "https://kupikod.com", "methods": ["sbp", "card"] },
            { "shop_name": "PlayerOK", "price": 415, "rating": "4.7", "url": "https://playerok.com", "methods": ["sbp", "card"] }
        ]
    },
    {
        "id": "genshin-980",
        "name": "980 + 110 Кристаллов",
        "category": "currency",
        "amount_text": "1090 кристаллов",
        "icon": "fa-solid fa-coins",
        "accent_color": "#A855F7",
        "prices": [
            { "shop_name": "Donatov.net", "price": 1290, "rating": "4.9", "url": "https://donatov.net", "methods": ["sbp", "card"] },
            { "shop_name": "Kupikod", "price": 1340, "rating": "4.8", "url": "https://kupikod.com", "methods": ["sbp", "card"] },
            { "shop_name": "PlayerOK", "price": 1270, "rating": "4.7", "url": "https://playerok.com", "methods": ["sbp", "crypto"] }
        ]
    }
]

class DevServerHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/track":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "Подписка успешно сохранена!"}).encode("utf-8"))
            return
        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # ── API ROUTES ───────────────────────────────────────────────────────
        if path == "/api/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "bot_username": "LootoZavr_bot"}).encode("utf-8"))
            return

        if path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "message": "LootoZavr Design Server"}).encode("utf-8"))
            return

        if path == "/api/catalog/popular":
            mode = query.get("mode", ["popular"])[0]
            games = list(MOCK_GAMES)
            if mode == "discount":
                games.sort(key=lambda x: x["discount_percent"], reverse=True)
            elif mode == "steam":
                games.sort(key=lambda x: int(x["steam_appid"]), reverse=True)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "games": games, "mode": mode}).encode("utf-8"))
            return

        if path == "/api/catalog/search":
            q = (query.get("query", [""])[0]).lower().strip()
            matches = [g for g in MOCK_GAMES if q in g["name"].lower()]
            donate_matches = [d for d in MOCK_DONATE_GAMES if q in d["name"].lower() or q in d["currency_name"].lower()]
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "games": matches or MOCK_GAMES[:4],
                "donate_games": donate_matches
            }).encode("utf-8"))
            return

        if re.match(r"^/api/prices/\d+/history$", path):
            # Price history chart
            timeline = [
                {"date": "2026-10-15", "min_price": 120, "avg_price": 240, "shop_count": 8},
                {"date": "2026-10-20", "min_price": 99, "avg_price": 210, "shop_count": 9},
                {"date": "2026-10-25", "min_price": 85, "avg_price": 195, "shop_count": 9},
                {"date": "2026-11-01", "min_price": 79, "avg_price": 180, "shop_count": 10},
                {"date": "2026-11-05", "min_price": 65, "avg_price": 160, "shop_count": 10},
                {"date": "2026-11-10", "min_price": 53, "avg_price": 150, "shop_count": 10},
                {"date": "2026-11-13", "min_price": 53, "avg_price": 145, "shop_count": 10},
            ]
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "game_id": 1,
                "game_name": "Cyberpunk 2077",
                "timeline": timeline,
                "all_time_low": 53,
                "current_best": 53,
                "is_atl": True
            }).encode("utf-8"))
            return

        if re.match(r"^/api/prices/\d+$", path):
            # Game detail prices
            m_id = int(re.search(r"\d+", path).group())
            game = next((g for g in MOCK_GAMES if g["id"] == m_id), MOCK_GAMES[0])
            items = [
                {
                    "shop_name": "FunPay",
                    "price": 53.0,
                    "url": "https://funpay.com",
                    "edition_name": "Standard Edition",
                    "platform": "Steam (Россия/СНГ)"
                },
                {
                    "shop_name": "Plati.market",
                    "price": 65.0,
                    "url": "https://plati.market",
                    "edition_name": "Standard Edition",
                    "platform": "Steam Key"
                },
                {
                    "shop_name": "GGSEL",
                    "price": 69.0,
                    "url": "https://ggsel.net",
                    "edition_name": "Standard Edition",
                    "platform": "Steam Key"
                },
                {
                    "shop_name": "Steampay",
                    "price": 119.0,
                    "url": "https://steampay.com",
                    "edition_name": "Standard Edition",
                    "platform": "Steam Gift"
                },
                {
                    "shop_name": "Steambuy",
                    "price": 125.0,
                    "url": "https://steambuy.com",
                    "edition_name": "Standard Edition",
                    "platform": "Steam Key"
                },
                {
                    "shop_name": "Zaka-Zaka",
                    "price": 139.0,
                    "url": "https://zaka-zaka.com",
                    "edition_name": "Standard Edition",
                    "platform": "Steam Key"
                },
                {
                    "shop_name": "GabeStore",
                    "price": 149.0,
                    "url": "https://gabestore.ru",
                    "edition_name": "Standard Edition",
                    "platform": "Steam Key"
                },
                {
                    "shop_name": "BattlePass",
                    "price": 155.0,
                    "url": "https://battlepass.ru",
                    "edition_name": "Standard Edition",
                    "platform": "Steam Account"
                }
            ]
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "game": game,
                "prices": items,
                "total_offers": len(items),
                "steam_official": {
                    "price_str": "2 499 ₽",
                    "raw_rub": 2499.0
                }
            }).encode("utf-8"))
            return

        if path == "/api/donate/games":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "games": MOCK_DONATE_GAMES}).encode("utf-8"))
            return

        if path.startswith("/api/donate/game/"):
            slug = path.replace("/api/donate/game/", "")
            game = next((d for d in MOCK_DONATE_GAMES if d["slug"] == slug), MOCK_DONATE_GAMES[0])
            game_data = dict(game)
            game_data["packages"] = MOCK_PACKAGES_GENSHIN
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "game": game_data}).encode("utf-8"))
            return

        # ── FRONTEND PAGES: Always serve templates/index.html ────────────────
        if path in ("/", "/topup", "/donate") or path.startswith("/donate/") or path.startswith("/game/"):
            if os.path.exists(TEMPLATE_PATH):
                with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
                return
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"templates/index.html not found")
                return

        # Default static file handling
        return super().do_GET()


def run():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), DevServerHandler) as httpd:
        print("=" * 60)
        print(" LOOTOZAVR — СЕРВЕР ДИЗАЙНА И ВЕРСТКИ (БЕЗ ДОКЕРА)")
        print("=" * 60)
        print(f" Сервер запущен:  http://localhost:{PORT}")
        print(f" Главная:        http://localhost:{PORT}/")
        print(f" Пополнение:     http://localhost:{PORT}/topup")
        print(f" Донат:          http://localhost:{PORT}/donate")
        print(f" Файл верстки:   {TEMPLATE_PATH}")
        print("=" * 60)
        print(" Нажмите Ctrl+C для остановки")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n Сервер остановлен.")


if __name__ == "__main__":
    run()
