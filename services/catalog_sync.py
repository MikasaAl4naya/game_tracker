import logging
import requests
from bs4 import BeautifulSoup
from sqlalchemy import select, func

from database import SyncSessionLocal
from models import GameCatalog, PriceResult
from services.filters import clean_game_name_for_search, matches_game_name
from services.parsers.base import get_http_session

logger = logging.getLogger(__name__)


def _parse_steamspy_owners(owners_str: str) -> int:
    """Парсит нижнюю границу диапазона владельцев из SteamSpy ('5,000,000 .. 10,000,000' → 5000000)."""
    try:
        return int(owners_str.split("..")[0].replace(",", "").strip())
    except Exception:
        return 0


def save_catalog_to_db(games_list: list[dict]) -> int:
    db = SyncSessionLocal()
    added_count = 0
    try:
        for g in games_list:
            existing = db.execute(
                select(GameCatalog).where(GameCatalog.name == g["name"])
            ).scalars().first()
            if not existing:
                new_game = GameCatalog(
                    name=g["name"],
                    url_funpay=g.get("url") or None,
                    steam_appid=g.get("steam_appid"),
                    steamspy_owners=g.get("steamspy_owners"),
                    is_free=g.get("is_free"),
                )
                db.add(new_game)
                added_count += 1
            else:
                if g.get("steam_appid") and not existing.steam_appid:
                    existing.steam_appid = g["steam_appid"]
                if g.get("steamspy_owners") and (not existing.steamspy_owners or g["steamspy_owners"] > existing.steamspy_owners):
                    existing.steamspy_owners = g["steamspy_owners"]
                if g.get("is_free") is not None and existing.is_free is None:
                    existing.is_free = g["is_free"]
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Ошибка сохранения каталога: %s", e)
    finally:
        db.close()
    return added_count


def sync_top_steam_games_logic() -> int:
    games_data = []
    session = get_http_session()
    try:
        for page in range(2):
            response = session.get(
                f"https://steamspy.com/api.php?request=all&page={page}", timeout=20
            )
            data = response.json()
            for appid, info in data.items():
                if not info.get("name"):
                    continue
                price = str(info.get("price", "0"))
                owners = _parse_steamspy_owners(info.get("owners", "0"))
                games_data.append({
                    "name": info["name"],
                    "url": "",
                    "steam_appid": int(appid),
                    "steamspy_owners": owners,
                    "is_free": price == "0",
                })
        added = save_catalog_to_db(games_data)
        logger.info("Steam sync: добавлено %d игр", added)
        return added
    except Exception as e:
        logger.error("Steam sync error: %s", e)
        return 0


def backfill_steamspy_stats_logic() -> int:
    db = SyncSessionLocal()
    session = get_http_session()
    try:
        owners_map: dict[int, int] = {}
        free_map: dict[int, bool] = {}
        for page in range(2):
            try:
                resp = session.get(
                    f"https://steamspy.com/api.php?request=all&page={page}", timeout=20
                )
                for appid_str, info in resp.json().items():
                    owners = _parse_steamspy_owners(info.get("owners", "0"))
                    if owners > 0:
                        owners_map[int(appid_str)] = owners
                    free_map[int(appid_str)] = str(info.get("price", "1")) == "0"
            except Exception as e:
                logger.warning("backfill_steamspy_stats page %d error: %s", page, e)

        if not owners_map:
            logger.warning("backfill_steamspy_stats: пустой ответ от SteamSpy")
            return 0

        games = db.execute(
            select(GameCatalog).where(GameCatalog.steam_appid.isnot(None))
        ).scalars().all()

        updated = 0
        for game in games:
            changed = False
            owners = owners_map.get(game.steam_appid)
            if owners and (not game.steamspy_owners or owners > game.steamspy_owners):
                game.steamspy_owners = owners
                changed = True
            if game.steam_appid in free_map and game.is_free is None:
                game.is_free = free_map[game.steam_appid]
                changed = True
            if changed:
                updated += 1

        db.commit()
        logger.info("backfill_steamspy_stats: обновлено %d из %d игр", updated, len(games))
        return updated
    except Exception as e:
        db.rollback()
        logger.error("backfill_steamspy_stats error: %s", e)
        return 0
    finally:
        db.close()


def backfill_steam_appids_logic() -> int:
    db = SyncSessionLocal()
    session = get_http_session()
    try:
        games = db.execute(
            select(GameCatalog)
            .outerjoin(PriceResult, GameCatalog.id == PriceResult.game_id)
            .where(GameCatalog.steam_appid.is_(None))
            .group_by(GameCatalog.id)
            .order_by(func.count(PriceResult.id).desc())
            .limit(200)
        ).scalars().all()
        if not games:
            logger.info("backfill_steam_appids: все игры уже имеют appid")
            return 0

        updated = 0
        for game in games:
            try:
                resp = session.get(
                    "https://store.steampowered.com/api/storesearch/",
                    params={"term": game.name, "l": "russian", "cc": "US"},
                    timeout=5,
                )
                items = resp.json().get("items", [])
                if items:
                    game.steam_appid = items[0]["id"]
                    updated += 1
            except Exception as e:
                logger.warning("backfill_steam_appids: ошибка для '%s': %s", game.name, e)

        db.commit()
        logger.info("backfill_steam_appids: обновлено %d записей из %d", updated, len(games))
        return updated
    except Exception as e:
        db.rollback()
        logger.error("backfill_steam_appids error: %s", e)
        return 0
    finally:
        db.close()


def sync_funpay_catalog_logic() -> int:
    session = get_http_session()
    try:
        soup = BeautifulSoup(
            session.get("https://funpay.com/", timeout=15).text,
            "html.parser",
        )
    except Exception as e:
        logger.error("FunPay catalog sync error: %s", e)
        return 0

    funpay_keys_map: dict[str, str] = {}
    for item in soup.find_all("div", class_="promo-game-item"):
        title_tag = item.find("div", class_="game-title")
        if not title_tag:
            continue
        target_url = next(
            (a.get("href") for a in item.find_all("a") if "ключ" in a.text.lower()),
            title_tag.a.get("href") if title_tag.a else None,
        )
        if title_tag.text.strip() and target_url:
            funpay_keys_map[clean_game_name_for_search(title_tag.text.strip()).lower()] = target_url

    db = SyncSessionLocal()
    updated_count = 0
    try:
        for game in db.execute(select(GameCatalog)).scalars().all():
            clean_db_name = clean_game_name_for_search(game.name).lower()
            matched_url = funpay_keys_map.get(clean_db_name) or next(
                (
                    fp_url for fp_name, fp_url in funpay_keys_map.items()
                    if matches_game_name(game.name, fp_name) or matches_game_name(fp_name, game.name)
                ),
                None,
            )
            if matched_url and game.url_funpay != matched_url:
                game.url_funpay = matched_url
                updated_count += 1
        db.commit()
        logger.info("FunPay sync завершён: обновлено %d ссылок", updated_count)
        return updated_count
    except Exception as e:
        db.rollback()
        logger.error("FunPay sync error: %s", e)
        return 0
    finally:
        db.close()
