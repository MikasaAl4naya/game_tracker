import logging
from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select, func

from database import SyncSessionLocal
from models import GameCatalog, PriceResult, UserTask
from services.config import NO_PRICE_LIMIT, REDIS_URL, RABBITMQ_URL, redis_client
from services.filters import (
    clean_game_name_for_search,
    matches_game_name,
    quick_reject,
    detect_region,
    detect_platform,
    check_lot_validity,
    parse_price,
)
from services.storage import save_prices
from services.catalog_sync import (
    save_catalog_to_db,
    sync_top_steam_games_logic,
    backfill_steamspy_stats_logic,
    backfill_steam_appids_logic,
    sync_funpay_catalog_logic,
)
from services.parsers import (
    parse_funpay,
    parse_plati,
    parse_steambuy,
    parse_steampay,
    parse_zakazaka,
    parse_ggsel,
    parse_gabestore,
    parse_gamerilla,
    parse_gamersbase,
    parse_keysforgamers,
)

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

celery_app = Celery(
    "tracker_worker",
    broker=RABBITMQ_URL,
    backend=f"{REDIS_URL}/0",
)


# ---------- ЗАДАЧИ ПАРСИНГА ----------

@celery_app.task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 5})
def parse_funpay_task(game_id: int, url: str, target_price: float, chat_id: int = 0, game_name: str = ""):
    prices = parse_funpay(game_id=game_id, url=url, target_price=target_price, game_name=game_name)
    if prices:
        save_prices(prices)


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 0, "countdown": 3})
def parse_plati_task(game_id: int, game_name: str, target_price: float, chat_id: int = 0):
    prices = parse_plati(game_id=game_id, game_name=game_name, target_price=target_price)
    if prices:
        save_prices(prices)


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 5})
def parse_steambuy_task(game_id: int, game_name: str, target_price: float, chat_id: int = 0):
    prices = parse_steambuy(game_id=game_id, game_name=game_name, target_price=target_price)
    if prices:
        save_prices(prices)


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 5})
def parse_steampay_task(game_id: int, game_name: str, target_price: float, chat_id: int = 0):
    prices = parse_steampay(game_id=game_id, game_name=game_name, target_price=target_price)
    if prices:
        save_prices(prices)


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 5})
def parse_zakazaka_task(game_id: int, game_name: str, target_price: float, chat_id: int = 0):
    prices = parse_zakazaka(game_id=game_id, game_name=game_name, target_price=target_price)
    if prices:
        save_prices(prices)


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 5})
def parse_ggsel_task(game_id: int, game_name: str, target_price: float, chat_id: int = 0):
    prices = parse_ggsel(game_id=game_id, game_name=game_name, target_price=target_price)
    if prices:
        save_prices(prices)


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 5})
def parse_gabestore_task(game_id: int, game_name: str, target_price: float, chat_id: int = 0):
    prices = parse_gabestore(game_id=game_id, game_name=game_name, target_price=target_price)
    if prices:
        save_prices(prices)


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 5})
def parse_gamerilla_task(game_id: int, game_name: str, target_price: float, chat_id: int = 0):
    prices = parse_gamerilla(game_id=game_id, game_name=game_name, target_price=target_price)
    if prices:
        save_prices(prices)


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 5})
def parse_gamersbase_task(game_id: int, game_name: str, target_price: float, chat_id: int = 0):
    prices = parse_gamersbase(game_id=game_id, game_name=game_name, target_price=target_price)
    if prices:
        save_prices(prices)


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 5})
def parse_keysforgamers_task(game_id: int, game_name: str, target_price: float, chat_id: int = 0):
    prices = parse_keysforgamers(game_id=game_id, game_name=game_name, target_price=target_price)
    if prices:
        save_prices(prices)


# ---------- СИНХРОНИЗАЦИЯ КАТАЛОГА ----------

@celery_app.task
def sync_top_steam_games():
    return sync_top_steam_games_logic()


@celery_app.task
def backfill_steamspy_stats():
    return backfill_steamspy_stats_logic()


@celery_app.task
def backfill_steam_appids():
    return backfill_steam_appids_logic()


@celery_app.task
def sync_funpay_catalog():
    return sync_funpay_catalog_logic()


@celery_app.task
def sync_donate_catalog_task():
    """Синхронизирует актуальные цены и пакеты для внутриигрового доната."""
    from services.donate_service import init_donate_database_logic
    try:
        success = init_donate_database_logic()
        logger.info("sync_donate_catalog_task executed successfully: %s", success)
        return success
    except Exception as e:
        logger.error("sync_donate_catalog_task error: %s", e)
        return False


# ---------- МАССОВЫЕ ЗАДАЧИ ----------

@celery_app.task
def trigger_all_price_checks():
    db = SyncSessionLocal()
    try:
        tracked_game_ids = db.execute(select(UserTask.game_id).distinct()).scalars().all()
        if not tracked_game_ids:
            return

        games = db.execute(
            select(GameCatalog).where(GameCatalog.id.in_(tracked_game_ids))
        ).scalars().all()

        for game in games:
            parse_plati_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_steambuy_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_steampay_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_ggsel_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_zakazaka_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_gabestore_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_gamerilla_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_gamersbase_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_keysforgamers_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            if game.url_funpay:
                parse_funpay_task.delay(game.id, game.url_funpay, NO_PRICE_LIMIT, 0, game.name)
    finally:
        db.close()


@celery_app.task
def fill_missing_prices(batch_size: int = 50):
    """Запускает парсинг только для платных игр, у которых ещё нет ни одной цены."""
    db = SyncSessionLocal()
    try:
        games_with_prices = select(PriceResult.game_id).distinct()
        empty_games = db.execute(
            select(GameCatalog)
            .where(GameCatalog.is_free.isnot(True))
            .where(GameCatalog.id.not_in(games_with_prices))
            .limit(batch_size)
        ).scalars().all()

        if not empty_games:
            logger.info("Все платные игры уже имеют цены — дозаполнение не требуется")
            return

        logger.info("Найдено %d игр без цен — запускаем парсинг", len(empty_games))
        for game in empty_games:
            parse_plati_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_steambuy_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_steampay_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_ggsel_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_zakazaka_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_gabestore_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_gamerilla_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_gamersbase_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_keysforgamers_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            if game.url_funpay:
                parse_funpay_task.delay(game.id, game.url_funpay, NO_PRICE_LIMIT, 0, game.name)
    except Exception as e:
        logger.error("Ошибка при дозаполнении: %s", e)
    finally:
        db.close()


@celery_app.task
def reparse_top_games(limit: int = 50):
    """Обновляет цены для топ-50 самых популярных платных игр каталога."""
    db = SyncSessionLocal()
    try:
        games = db.execute(
            select(GameCatalog)
            .where(GameCatalog.is_free.isnot(True))
            .order_by(GameCatalog.steamspy_owners.desc().nullslast())
            .limit(limit)
        ).scalars().all()

        for game in games:
            parse_plati_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_steambuy_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_steampay_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_ggsel_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_zakazaka_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_gabestore_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_gamerilla_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_gamersbase_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_keysforgamers_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            if game.url_funpay:
                parse_funpay_task.delay(game.id, game.url_funpay, NO_PRICE_LIMIT, 0, game.name)

        logger.info("reparse_top_games: запущено обновление для %d топ-игр", len(games))
    except Exception as e:
        logger.error("reparse_top_games error: %s", e)
    finally:
        db.close()


@celery_app.task
def reparse_all_games(batch: int = 0, batch_size: int = 100):
    """Запускает все парсеры для всех платных игр каталога батчами."""
    db = SyncSessionLocal()
    try:
        games = db.execute(
            select(GameCatalog)
            .where(GameCatalog.is_free.isnot(True))
            .outerjoin(PriceResult, GameCatalog.id == PriceResult.game_id)
            .group_by(GameCatalog.id)
            .order_by(func.count(PriceResult.id).desc())
            .offset(batch * batch_size)
            .limit(batch_size)
        ).scalars().all()

        if not games:
            logger.info("reparse_all_games: всё готово, батч %d пустой", batch)
            return

        for game in games:
            parse_plati_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_steambuy_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_steampay_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_ggsel_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_zakazaka_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_gabestore_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_gamerilla_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_gamersbase_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            parse_keysforgamers_task.delay(game.id, game.name, NO_PRICE_LIMIT, 0)
            if game.url_funpay:
                parse_funpay_task.delay(game.id, game.url_funpay, NO_PRICE_LIMIT, 0, game.name)

        logger.info("reparse_all_games: батч %d — запущено %d игр", batch, len(games))

        if len(games) == batch_size:
            reparse_all_games.apply_async(
                kwargs={"batch": batch + 1, "batch_size": batch_size},
                countdown=300,
            )
    except Exception as e:
        logger.error("reparse_all_games error: %s", e)
    finally:
        db.close()


# ---------- РАСПИСАНИЕ CELERY BEAT ----------

celery_app.conf.beat_schedule = {
    # 1. Проверка цен для отслеживаемых пользователями игр (каждые 4 часа)
    "check-tracked-prices-every-4-hours": {
        "task": "worker.trigger_all_price_checks",
        "schedule": 14_400.0,
    },
    # 2. Обновление цен для топ-50 популярных игр каталога (каждые 6 часов)
    "reparse-top-games-every-6-hours": {
        "task": "worker.reparse_top_games",
        "schedule": 21_600.0,
    },
    # 3. Полный фоновый перепарсинг всех платных игр каталога батчами (ежедневно ночью в 01:00 МСК)
    "reparse-all-catalog-games-daily": {
        "task": "worker.reparse_all_games",
        "schedule": crontab(hour=1, minute=0),
    },
    # 4. Дозаполнение цен для игр без предложений (каждые 3 часа)
    "fill-missing-prices-every-3-hours": {
        "task": "worker.fill_missing_prices",
        "schedule": 10_800.0,
    },
    # 5. Синхронизация топа Steam, владельцев SteamSpy и валютных курсов (ночью в 03:00 МСК)
    "update-steam-top-every-night": {
        "task": "worker.sync_top_steam_games",
        "schedule": crontab(hour=3, minute=0),
    },
    # 6. Синхронизация каталога категорий FunPay (еженедельно по понедельникам в 04:00 МСК)
    "sync-funpay-catalog-weekly": {
        "task": "worker.sync_funpay_catalog",
        "schedule": crontab(hour=4, minute=0, day_of_week=1),
    },
    # 7. Синхронизация каталога и цен доната в играх (каждые 12 часов)
    "sync-donate-catalog-every-12-hours": {
        "task": "worker.sync_donate_catalog_task",
        "schedule": 43_200.0,
    },
}
celery_app.conf.timezone = "Europe/Moscow"
