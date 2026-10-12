from contextlib import asynccontextmanager
from datetime import datetime

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import engine, Base, get_db
from models import GameCatalog, UserTask, PriceResult
from worker import (
    NO_PRICE_LIMIT,
    parse_funpay_task, parse_plati_task, parse_steambuy_task,
    parse_ggsel_task, parse_zakazaka_task,
    sync_top_steam_games, trigger_all_price_checks,
    sync_funpay_catalog, fill_missing_prices,
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


app = FastAPI(title="GameDeals API", lifespan=lifespan)

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
        parse_funpay_task.delay(game_id, url_funpay, NO_PRICE_LIMIT, 0)
    parse_plati_task.delay(game_id, game_name, NO_PRICE_LIMIT, 0)
    parse_steambuy_task.delay(game_id, game_name, NO_PRICE_LIMIT, 0)
    parse_ggsel_task.delay(game_id, game_name, NO_PRICE_LIMIT, 0)
    parse_zakazaka_task.delay(game_id, game_name, NO_PRICE_LIMIT, 0)


# ---------- ЭНДПОИНТЫ ----------

@app.get("/")
async def serve_frontend():
    return FileResponse("templates/index.html")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Агрегатор работает!"}


@app.get("/api/catalog/")
async def get_catalog_list(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GameCatalog).order_by(GameCatalog.id).limit(24))
    games = result.scalars().all()
    return [{"id": g.id, "name": g.name} for g in games]


@app.get("/api/catalog/search")
async def search_games(query: str, db: AsyncSession = Depends(get_db)):
    stmt = select(GameCatalog).where(GameCatalog.name.ilike(f"%{query}%"))
    result = await db.execute(stmt)
    games = result.scalars().all()

    if games:
        return {
            "status": "success",
            "source": "local_db",
            "found": len(games),
            "games": [{"id": g.id, "name": g.name} for g in games],
        }

    print(f"[ПОИСК] Игры '{query}' нет в базе — ищу в Steam...")
    official_name = query

    async with httpx.AsyncClient() as client:
        search_url = f"https://store.steampowered.com/api/storesearch/?term={query}&l=russian&cc=US"
        try:
            resp = await client.get(search_url, timeout=5.0)
            search_data = resp.json()
            if search_data.get("items"):
                official_name = search_data["items"][0]["name"]
                print(f"[ПОИСК] Steam нашёл: {official_name}")
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
            "found": 1,
            "games": [{"id": existing.id, "name": existing.name}],
        }

    new_game = GameCatalog(name=official_name)
    db.add(new_game)
    await db.commit()
    await db.refresh(new_game)
    return {
        "status": "success",
        "source": "auto_added",
        "found": 1,
        "games": [{"id": new_game.id, "name": new_game.name}],
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
        unique_key = f"{p.shop_name.split(' (')[0]}_{p.region}"
        if unique_key not in seen_shops:
            current_offers.append({
                "id": p.id,
                "shop": p.shop_name,
                "price": p.price,
                "lot_name": p.lot_name,
                "url": p.lot_url,
                "region": p.region,
                "date": p.timestamp.strftime("%Y-%m-%d %H:%M"),
            })
            seen_shops.add(unique_key)

    steam_prices = await get_steam_regional_prices(game.name)

    return {
        "status": "success",
        "game_name": game.name,
        "steam_official": steam_prices,
        "current_offers": current_offers,
        "last_update": last_update.isoformat() if last_update else None,
        "updating": needs_update,
    }


@app.post("/api/tasks/force_check")
async def force_check_all_prices():
    trigger_all_price_checks.delay()
    return {"status": "success", "message": "Все воркеры запущены принудительно!"}


@app.post("/api/tasks/fill_missing")
async def trigger_smart_fill():
    fill_missing_prices.delay()
    return {"status": "success", "message": "Запущен сбор цен для игр без данных."}


@app.get("/api/featured")
async def get_featured_games():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://store.steampowered.com/api/featuredcategories/?l=russian",
                timeout=5.0,
            )
            data = resp.json()

            games = []
            seen_names: set[str] = set()

            for cat in ("top_sellers", "new_releases", "specials"):
                for g in data.get(cat, {}).get("items", []):
                    name = g.get("name")
                    if name and name not in seen_names:
                        seen_names.add(name)
                        games.append({"name": name, "image": g.get("header_image")})
                    if len(games) == 10:
                        return {"status": "success", "games": games}

            return {"status": "success", "games": games}
        except Exception as e:
            print(f"Ошибка Steam API (Featured): {e}")
            return {"status": "error", "games": []}
