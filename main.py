import os
from contextlib import asynccontextmanager
from datetime import datetime

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy import func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import engine, Base, get_db
from models import GameCatalog, UserTask, PriceResult, DonateGame
from services.seo import render_html_with_seo
from worker import (
    NO_PRICE_LIMIT,
    parse_funpay_task, parse_plati_task, parse_steambuy_task,
    parse_steampay_task, parse_ggsel_task, parse_zakazaka_task,
    parse_gabestore_task, parse_gamerilla_task, parse_gamersbase_task,
    parse_keysforgamers_task,
    sync_top_steam_games, trigger_all_price_checks,
    sync_funpay_catalog, fill_missing_prices, backfill_steam_appids,
    backfill_steamspy_stats, reparse_all_games,
)

# Курсы для конвертации цен Steam в рубли
STEAM_EXCHANGE_RATES: dict[str, float] = {
    "RUB": 1.0,
    "KZT": 0.20,
    "USD": 100.0,
    "TRY": 2.90,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="LootoZavr API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- МОДЕЛИ ЗАПРОСОВ ----------

class GameCreateRequest(BaseModel):
    name: str
    url_funpay: str | None = None


class TaskCreateRequest(BaseModel):
    game_name: str
    target_price: float
    chat_id: int


# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------

async def get_steam_regional_prices(game_name: str) -> dict:
    prices_data: dict = {
        "Россия": "Недоступно",
        "Казахстан": "Недоступно",
        "Турция": "Недоступно",
        "raw_rub": None,
    }

    async with httpx.AsyncClient() as client:
        search_url = f"https://store.steampowered.com/api/storesearch/?term={game_name}&l=russian&cc=US"
        try:
            resp = await client.get(search_url, timeout=5.0)
            search_data = resp.json()
            if not search_data.get("items"):
                return prices_data

            app_id = search_data["items"][0]["id"]
            regions = {"RU": "Россия", "KZ": "Казахстан", "TR": "Турция"}

            for cc, label in regions.items():
                price_url = (
                    f"https://store.steampowered.com/api/appdetails"
                    f"?appids={app_id}&cc={cc}&filters=price_overview"
                )
                p_resp = await client.get(price_url, timeout=5.0)
                p_data = p_resp.json()

                if p_data and p_data.get(str(app_id), {}).get("success"):
                    overview = p_data[str(app_id)]["data"].get("price_overview")
                    if overview:
                        original_price = overview["final"] / 100
                        currency = overview["currency"]
                        rate = STEAM_EXCHANGE_RATES.get(currency)
                        if rate:
                            price_in_rub = int(original_price * rate)
                            prices_data[label] = f"~{price_in_rub} ₽"
                            if not prices_data["raw_rub"] or cc == "RU":
                                prices_data["raw_rub"] = price_in_rub
                        else:
                            prices_data[label] = f"{original_price} {currency}"
        except Exception as e:
            print(f"Ошибка Steam API: {e}")

    return prices_data


def run_price_update(game_id: int, game_name: str, url_funpay: str | None = None) -> None:
    if url_funpay:
        parse_funpay_task.delay(game_id, url_funpay, NO_PRICE_LIMIT, 0, game_name)
    parse_plati_task.delay(game_id, game_name, NO_PRICE_LIMIT, 0)
    parse_steambuy_task.delay(game_id, game_name, NO_PRICE_LIMIT, 0)
    parse_steampay_task.delay(game_id, game_name, NO_PRICE_LIMIT, 0)
    parse_ggsel_task.delay(game_id, game_name, NO_PRICE_LIMIT, 0)
    parse_zakazaka_task.delay(game_id, game_name, NO_PRICE_LIMIT, 0)
    parse_gabestore_task.delay(game_id, game_name, NO_PRICE_LIMIT, 0)
    parse_gamerilla_task.delay(game_id, game_name, NO_PRICE_LIMIT, 0)
    parse_gamersbase_task.delay(game_id, game_name, NO_PRICE_LIMIT, 0)
    parse_keysforgamers_task.delay(game_id, game_name, NO_PRICE_LIMIT, 0)


# ---------- ЭНДПОИНТЫ ----------

@app.get("/")
async def serve_frontend(request: Request):
    html_content = render_html_with_seo(page_url=str(request.base_url))
    return HTMLResponse(content=html_content)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/topup")
async def serve_topup_page(request: Request):
    html_content = render_html_with_seo(
        page_url=str(request.url),
        custom_title="Где пополнить Steam в 2026 году: сравнение сервисов и комиссий | LootoZavr",
        custom_description="Где выгоднее и быстрее пополнить баланс Steam в России в 2026 году. Честное сравнение 25 проверенных сервисов: FunPay, GGSEL, Steamgold, МТС, Элекснет и др. Интерактивный калькулятор переплаты.",
    )
    return HTMLResponse(content=html_content)


@app.get("/donate")
async def serve_donate_page(request: Request):
    html_content = render_html_with_seo(
        page_url=str(request.url),
        custom_title="Донат в игры 2026: Genshin, Honkai, Brawl Stars, Roblox — Сравнение цен | LootoZavr",
        custom_description="Агрегатор и сравнение цен на донат в играх: Genshin Impact, Honkai: Star Rail, ZZZ, Brawl Stars, Roblox, PUBG Mobile. Цены Donatov.net, Kupikod, PlayerOK, FunPay, LootBar, GGSEL. Моментальное пополнение по UID без передачи аккаунта.",
    )
    return HTMLResponse(content=html_content)


@app.get("/donate/{game_slug}")
async def serve_donate_game_page(game_slug: str, request: Request):
    from services.donate_service import get_donate_game_by_slug
    game = get_donate_game_by_slug(game_slug)
    if not game:
        html_content = render_html_with_seo(
            page_url=str(request.url),
            custom_title="Донат в игры — Сравнение цен и магазинов | LootoZavr",
            custom_description="Сравнение цен на донат и пропуска в популярных играх.",
        )
    else:
        name = game["name"]
        curr = game["currency_name"]
        html_content = render_html_with_seo(
            page_url=str(request.url),
            custom_title=f"Купить донат {name} дешево — {curr}, Пропуск, Луна | Сравнение цен | LootoZavr",
            custom_description=f"Где дешевле купить {curr} и пропуска в {name}? Сравнение цен Donatov.net, Kupikod, PlayerOK, FunPay, GGSEL. Пополнение по {game['id_type']} без передачи пароля. Скидки по промокоду LOOTOZAVR.",
        )
    return HTMLResponse(content=html_content)


@app.get("/game/{game_id}")
async def serve_game_page(game_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    game = await db.get(GameCatalog, game_id)
    if not game:
        html_content = render_html_with_seo(page_url=str(request.url))
        return HTMLResponse(content=html_content)

    res = await db.execute(select(PriceResult).where(PriceResult.game_id == game_id))
    prices = res.scalars().all()
    valid_prices = [p.price for p in prices if p.price >= 50 and p.shop_name not in {"GGSEL", "WMCentre", "Plati"}]
    min_price = min(valid_prices, default=None)
    offer_count = len(valid_prices)

    html_content = render_html_with_seo(
        game_name=game.name,
        min_price=min_price,
        offer_count=offer_count,
        steam_appid=game.steam_appid,
        page_url=str(request.url),
    )
    return HTMLResponse(content=html_content)


@app.get("/sitemap.xml")
async def serve_sitemap(request: Request, db: AsyncSession = Depends(get_db)):
    base_url = str(request.base_url).rstrip("/")
    result = await db.execute(select(GameCatalog.id).order_by(GameCatalog.id))
    game_ids = result.scalars().all()

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        f'  <url><loc>{base_url}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>',
        f'  <url><loc>{base_url}/topup</loc><changefreq>daily</changefreq><priority>0.9</priority></url>',
        f'  <url><loc>{base_url}/donate</loc><changefreq>daily</changefreq><priority>0.9</priority></url>',
    ]
    for gid in game_ids:
        xml_lines.append(
            f'  <url><loc>{base_url}/game/{gid}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>'
        )

    from services.donate_service import get_all_donate_games
    try:
        donate_games = get_all_donate_games()
        for dg in donate_games:
            xml_lines.append(
                f'  <url><loc>{base_url}/donate/{dg["slug"]}</loc><changefreq>daily</changefreq><priority>0.8</priority></url>'
            )
    except Exception:
        pass

    xml_lines.append('</urlset>')

    return Response(content="\n".join(xml_lines), media_type="application/xml")


@app.get("/robots.txt")
async def serve_robots(request: Request):
    base_url = str(request.base_url).rstrip("/")
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Allow: /game/\n"
        "Allow: /topup\n"
        "Allow: /donate\n"
        "Allow: /donate/\n"
        "Disallow: /api/\n\n"
        f"Sitemap: {base_url}/sitemap.xml\n"
    )
    return Response(content=content, media_type="text/plain")


@app.get("/api/donate/games")
async def api_get_donate_games():
    from services.donate_service import get_all_donate_games
    games = get_all_donate_games()
    return {"status": "success", "games": games}


@app.get("/api/donate/game/{slug}")
async def api_get_donate_game(slug: str):
    from services.donate_service import get_donate_game_by_slug
    game = get_donate_game_by_slug(slug)
    if not game:
        raise HTTPException(status_code=404, detail="Игра для доната не найдена")
    return {"status": "success", "game": game}


@app.post("/api/donate/init")
async def api_init_donate_database():
    from services.donate_service import init_donate_database_logic
    ok = init_donate_database_logic()
    return {"status": "success" if ok else "error", "message": "База данных доната обновлена"}



@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Агрегатор работает!"}


@app.get("/api/config")
async def get_public_config():
    bot_user = os.getenv("TELEGRAM_BOT_USERNAME", "LootoZavr_bot").strip().lstrip("@")
    return {
        "status": "success",
        "bot_username": bot_user or "LootoZavr_bot",
    }


@app.get("/api/catalog/")
async def get_catalog_list(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GameCatalog).order_by(GameCatalog.id).limit(24))
    games = result.scalars().all()
    return [{"id": g.id, "name": g.name} for g in games]


@app.get("/api/catalog/search")
async def search_games(query: str, db: AsyncSession = Depends(get_db)):
    clean_q = query.strip()
    if not clean_q:
        return {"status": "success", "found": 0, "donate_games": [], "games": []}

    # Поиск по каталогу доната
    donate_stmt = (
        select(DonateGame)
        .where(
            DonateGame.name.ilike(f"%{clean_q}%")
            | DonateGame.currency_name.ilike(f"%{clean_q}%")
            | DonateGame.slug.ilike(f"%{clean_q}%")
        )
        .order_by(DonateGame.sort_order)
    )
    donate_res = await db.execute(donate_stmt)
    matching_donate_games = donate_res.scalars().all()
    donate_games_data = [
        {
            "id": dg.id,
            "slug": dg.slug,
            "name": dg.name,
            "publisher": dg.publisher,
            "icon_url": dg.icon_url,
            "currency_name": dg.currency_name,
            "id_type": dg.id_type,
            "is_donate": True,
        }
        for dg in matching_donate_games
    ]

    # Поиск по каталогу игр Steam
    stmt = (
        select(GameCatalog)
        .where(GameCatalog.name.ilike(f"%{clean_q}%"))
        .order_by(
            case(
                (func.lower(GameCatalog.name) == clean_q.lower(), 0),
                (func.lower(GameCatalog.name).startswith(clean_q.lower() + " "), 1),
                (func.lower(GameCatalog.name).startswith(clean_q.lower()), 2),
                else_=3,
            ),
            GameCatalog.steamspy_owners.desc().nullslast(),
            func.length(GameCatalog.name).asc(),
        )
    )
    result = await db.execute(stmt)
    games = result.scalars().all()

    if games or donate_games_data:
        return {
            "status": "success",
            "source": "local_db",
            "found": len(games) + len(donate_games_data),
            "donate_games": donate_games_data,
            "games": [
                {
                    "id": g.id,
                    "name": g.name,
                    "steam_appid": g.steam_appid,
                }
                for g in games
            ],
        }

    print(f"[ПОИСК] Игры '{query}' нет в базе — ищу в Steam...")
    official_name = query
    steam_appid = None

    async with httpx.AsyncClient() as client:
        search_url = f"https://store.steampowered.com/api/storesearch/?term={query}&l=russian&cc=US"
        try:
            resp = await client.get(search_url, timeout=5.0)
            search_data = resp.json()
            if search_data.get("items"):
                official_name = search_data["items"][0]["name"]
                steam_appid = search_data["items"][0]["id"]
                print(f"[ПОИСК] Steam нашёл: {official_name} (appid: {steam_appid})")
            else:
                print(f"[ПОИСК] Steam не нашёл игру, сохраняем как есть: {official_name}")
        except Exception as e:
            print(f"[ПОИСК] Ошибка Steam API: {e}")

    existing = (await db.execute(
        select(GameCatalog).where(GameCatalog.name == official_name)
    )).scalars().first()

    if existing:
        return {
            "status": "success",
            "source": "local_db",
            "found": 1 + len(donate_games_data),
            "donate_games": donate_games_data,
            "games": [{"id": existing.id, "name": existing.name, "steam_appid": existing.steam_appid}],
        }

    new_game = GameCatalog(name=official_name, steam_appid=steam_appid)
    db.add(new_game)
    await db.commit()
    await db.refresh(new_game)
    return {
        "status": "success",
        "source": "auto_added",
        "found": 1 + len(donate_games_data),
        "donate_games": donate_games_data,
        "games": [{"id": new_game.id, "name": new_game.name, "steam_appid": new_game.steam_appid}],
    }


@app.post("/api/catalog")
async def add_game_to_catalog(game: GameCreateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GameCatalog).where(GameCatalog.name == game.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Эта игра уже есть в каталоге!")

    new_game = GameCatalog(name=game.name, url_funpay=game.url_funpay)
    db.add(new_game)
    await db.commit()
    await db.refresh(new_game)
    return {"status": "success", "game_id": new_game.id}


@app.post("/api/catalog/sync")
async def trigger_catalog_sync():
    sync_top_steam_games.delay()
    return {"status": "success", "message": "Паук Steam запущен."}


@app.post("/api/catalog/sync_funpay")
async def trigger_funpay_sync():
    sync_funpay_catalog.delay()
    return {"status": "success", "message": "Паук FunPay запущен! Он ищет ссылки для всех игр в базе."}


@app.post("/api/track")
async def add_tracking_task(task: TaskCreateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GameCatalog).where(GameCatalog.name.ilike(f"%{task.game_name}%")))
    game = result.scalars().first()

    if not game:
        raise HTTPException(status_code=404, detail=f"Игра '{task.game_name}' не найдена!")

    new_task = UserTask(game_id=game.id, target_price=task.target_price, chat_id=task.chat_id)
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    run_price_update(game.id, game.name, game.url_funpay)
    return {"status": "success", "task_id": new_task.id, "message": f"Ищем '{game.name}' везде!"}


@app.get("/api/prices/{game_id}")
async def get_game_prices(
    game_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    game = await db.get(GameCatalog, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Игра не найдена")

    prices_result = await db.execute(
        select(PriceResult)
        .where(PriceResult.game_id == game_id)
        .order_by(PriceResult.timestamp.desc())
    )
    prices = prices_result.scalars().all()

    last_update = prices[0].timestamp if prices else None
    needs_update = not last_update or (datetime.utcnow() - last_update).total_seconds() > 600

    if needs_update:
        background_tasks.add_task(run_price_update, game_id, game.name, game.url_funpay)

    legacy_shops = {"GGSEL", "WMCentre", "Plati"}
    current_offers = []
    seen_shops: set[str] = set()

    for p in prices:
        if p.shop_name in legacy_shops:
            continue
        platform = getattr(p, "platform", None) or "Steam"
        unique_key = f"{p.shop_name.split(' (')[0]}_{p.region}_{platform}"
        if unique_key not in seen_shops:
            current_offers.append({
                "id": p.id,
                "shop": p.shop_name,
                "price": p.price,
                "lot_name": p.lot_name,
                "url": p.lot_url,
                "region": p.region,
                "platform": platform,
                "date": p.timestamp.strftime("%Y-%m-%d %H:%M"),
            })
            seen_shops.add(unique_key)

    steam_prices = await get_steam_regional_prices(game.name)
    min_ever = min((o["price"] for o in current_offers), default=None)

    return {
        "status": "success",
        "game_id": game.id,
        "game_name": game.name,
        "steam_appid": game.steam_appid,
        "steam_official": steam_prices,
        "current_offers": current_offers,
        "min_ever": min_ever,
        "last_update": last_update.isoformat() if last_update else None,
        "updating": needs_update,
    }


@app.get("/api/prices/{game_id}/history")
async def get_price_history(game_id: int, db: AsyncSession = Depends(get_db)):
    from collections import defaultdict
    from datetime import datetime

    game = await db.get(GameCatalog, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Игра не найдена")

    stmt = (
        select(PriceResult)
        .where(PriceResult.game_id == game_id)
        .where(PriceResult.price >= 50.0)
        .where(PriceResult.price <= 35000.0)
        .order_by(PriceResult.timestamp.asc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    if not records:
        return {
            "status": "success",
            "game_id": game.id,
            "game_name": game.name,
            "min_ever": None,
            "all_time_low": None,
            "current_best": None,
            "timeline": [],
            "history": [],
        }

    history = [
        {
            "id": r.id,
            "shop": r.shop_name,
            "price": r.price,
            "region": r.region,
            "platform": getattr(r, "platform", None) or "Steam",
            "date": r.timestamp.strftime("%d.%m %H:%M"),
            "timestamp": r.timestamp.isoformat(),
        }
        for r in records
    ]

    # Хронологическая агрегация данных для чистого графика (без пилообразных скачков)
    first_ts = records[0].timestamp
    last_ts = records[-1].timestamp
    span_days = (last_ts - first_ts).days
    days = {r.timestamp.strftime("%Y-%m-%d") for r in records}
    use_daily = len(days) >= 3 or span_days >= 3

    buckets = defaultdict(list)
    for r in records:
        fmt = "%Y-%m-%d" if use_daily else "%Y-%m-%d %H:00"
        buckets[r.timestamp.strftime(fmt)].append(r)

    timeline = []
    for k in sorted(buckets.keys()):
        items = buckets[k]
        best = min(items, key=lambda x: x.price)
        avg = round(sum(x.price for x in items) / len(items), 1)
        dt = datetime.strptime(k, "%Y-%m-%d" if use_daily else "%Y-%m-%d %H:00")
        display_date = dt.strftime("%d.%m" if use_daily else "%d.%m %H:%M")
        timeline.append({
            "date": k,
            "display_date": display_date,
            "min_price": best.price,
            "best_shop": best.shop_name,
            "avg_price": avg,
            "offers_count": len(items),
        })

    atl_record = min(records, key=lambda x: x.price)
    latest_bucket_key = sorted(buckets.keys())[-1]
    latest_items = buckets[latest_bucket_key]
    curr_best_record = min(latest_items, key=lambda x: x.price)

    atl_price = atl_record.price
    curr_price = curr_best_record.price
    diff_pct = round(((curr_price - atl_price) / atl_price) * 100, 1) if atl_price > 0 else 0.0

    return {
        "status": "success",
        "game_id": game.id,
        "game_name": game.name,
        "min_ever": atl_price,
        "all_time_low": {
            "price": atl_price,
            "shop": atl_record.shop_name,
            "date": atl_record.timestamp.strftime("%d.%m.%Y"),
            "display_date": atl_record.timestamp.strftime("%d.%m"),
        },
        "current_best": {
            "price": curr_price,
            "shop": curr_best_record.shop_name,
        },
        "atl_diff_pct": diff_pct,
        "is_atl": curr_price <= atl_price * 1.02,
        "timeline": timeline,
        "history": history,
    }


@app.post("/api/tasks/force_check")
async def force_check_all_prices():
    trigger_all_price_checks.delay()
    return {"status": "success", "message": "Все воркеры запущены принудительно!"}


@app.post("/api/tasks/fill_missing")
async def trigger_smart_fill():
    fill_missing_prices.delay()
    return {"status": "success", "message": "Запущен сбор цен для игр без данных."}


@app.post("/api/catalog/backfill_appids")
async def trigger_backfill_appids():
    backfill_steam_appids.delay()
    return {"status": "success", "message": "Запущен сбор Steam AppID для игр в каталоге."}


@app.post("/api/catalog/backfill_stats")
async def trigger_backfill_stats():
    backfill_steamspy_stats.delay()
    return {"status": "success", "message": "Запущен сбор статистики SteamSpy."}


@app.post("/api/tasks/reparse_all")
async def trigger_reparse_all():
    reparse_all_games.delay(batch=0, batch_size=100)
    return {"status": "success", "message": "Запущен полный перепарсинг всех игр батчами по 100."}


@app.get("/api/catalog/popular")
async def get_popular_games(mode: str = "popular", db: AsyncSession = Depends(get_db)):
    """Игры с ценами: популярные, новинки или с лучшими ценами."""
    from sqlalchemy import func
    stmt = (
        select(
            GameCatalog.id,
            GameCatalog.name,
            GameCatalog.steam_appid,
            GameCatalog.steamspy_owners,
            func.count(PriceResult.id).label("offer_count"),
            func.min(PriceResult.price).label("min_price"),
            func.max(PriceResult.price).label("max_price"),
        )
        .join(PriceResult, GameCatalog.id == PriceResult.game_id)
        .where(GameCatalog.is_free.isnot(True))
        .where(PriceResult.price >= 50.0)
        .where(PriceResult.price <= 35000.0)
    )

    # Исключаем не-игры (утилиты, обои, саундтреки, серверы)
    non_game_keywords = ["wallpaper engine", "soundtrack", "server", "benchmark", "dedicated server"]
    for kw in non_game_keywords:
        stmt = stmt.where(~GameCatalog.name.ilike(f"%{kw}%"))

    stmt = stmt.group_by(GameCatalog.id, GameCatalog.name, GameCatalog.steam_appid, GameCatalog.steamspy_owners)

    if mode == "deals":
        stmt = stmt.where(PriceResult.price >= 50.0)
        stmt = stmt.having(func.count(PriceResult.id) >= 3)
        stmt = stmt.order_by(func.min(PriceResult.price).asc(), func.count(PriceResult.id).desc())
    elif mode == "popular":
        stmt = stmt.order_by(func.count(PriceResult.id).desc(), func.min(PriceResult.price).asc())
    else:  # "steam"
        stmt = stmt.order_by(
            func.coalesce(GameCatalog.steamspy_owners, 0).desc(),
            func.count(PriceResult.id).desc(),
        )

    stmt = stmt.limit(15)
    result = await db.execute(stmt)
    games = result.all()

    games_list = []
    for g in games:
        min_p = float(g.min_price) if g.min_price else None
        max_p = float(g.max_price) if getattr(g, "max_price", None) else None
        discount_pct = None
        if min_p and max_p and max_p > min_p:
            discount_pct = min(90, max(15, int(round((1 - min_p / max_p) * 100))))
        elif mode == "deals" and min_p:
            base_est = max(min_p * 1.7, min_p + 350)
            max_p = base_est
            discount_pct = min(85, max(25, int(round((1 - min_p / base_est) * 100))))

        games_list.append({
            "id": g.id,
            "name": g.name,
            "offer_count": g.offer_count,
            "min_price": int(min_p) if min_p else None,
            "max_price": int(max_p) if max_p else None,
            "discount_percent": discount_pct,
            "steam_appid": g.steam_appid,
        })

    return {
        "status": "success",
        "mode": mode,
        "games": games_list,
    }


@app.get("/api/featured")
async def get_featured_games(db: AsyncSession = Depends(get_db)):
    """Топ игр Steam из каталога с официальными изображениями."""
    result = await get_popular_games(mode="steam", db=db)
    games = [
        {
            "id": g["id"],
            "name": g["name"],
            "steam_appid": g["steam_appid"],
            "min_price": g["min_price"],
            "offer_count": g["offer_count"],
            "image": f"https://cdn.akamai.steamstatic.com/steam/apps/{g['steam_appid']}/header.jpg" if g["steam_appid"] else None,
        }
        for g in result.get("games", [])
    ]
    return {"status": "success", "games": games}
