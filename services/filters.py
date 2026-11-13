import re
from datetime import datetime

_HARDWARE_KEYWORDS = (
    "nvidia", "rtx", "гпу", "gpu", "видеокарт", "radeon", "rx ", "amd ", "intel ",
)


def check_lot_validity(name: str, props: str, strict_key_check: bool = True) -> bool:
    """Классический фильтр на регулярках (запасной вариант при недоступности LLM)."""
    name_lower = name.lower()
    text_to_check = (name + " " + props).lower()

    if any(kw in name_lower for kw in _HARDWARE_KEYWORDS):
        return False

    aggressive = (
        "аккаунт", "account", "оффлайн", "офлайн", "offline", "shared",
        "аренда", "дополнен", "улучшен", "season pass", "expansion", "dlc",
        "pack", "voice", "soundtrack", "artbook",
        "points", "coins", "credits", "skin", "набор", "denuvo",
        "hack", "cheat", "cheats", "hook", "aimbot", "wallhack", "кряк",
        # Внутриигровые предметы и валюта
        "сфер", "валют", "монет", "orb", "gems", "currency", "in-game", "ingame",
        "item", "предмет", "fragment", "token", "жетон",
    )
    if any(kw in name_lower for kw in aggressive):
        return False

    if re.search(r"\b(guard|вход)\b", name_lower):
        return False

    if re.search(r"\d+\s*(месяц|месяца|месяцев|день|дн[её]й|дня|week|weeks)\b", name_lower):
        return False

    desc_stop = (
        "общий аккаунт", "выданными данными", "смена пароля", "без смены данных",
        "запустите игру один раз", "логин:пароль", "смена аккаунтов",
        "переключить клиент steam",
    )
    if any(phrase in text_to_check for phrase in desc_stop):
        return False

    if strict_key_check:
        if not any(w in text_to_check for w in ("цифровой ключ", "key", "ключ", "гифт", "gift", "подарок", "код", "code")):
            return False

    return True


def quick_reject(name: str, props: str) -> bool:
    """Быстрый отсев очевидного мусора перед отправкой в LLM."""
    name_lower = name.lower()
    # "аккаунт/account" в названии лота — явная продажа аккаунта
    if "аккаунт" in name_lower or "account" in name_lower:
        return True

    text = (name + " " + props).lower()
    # Простая транслитерация гомоглифов: Н→H, А→A, E→E, O→O (только в оригинальном тексте)
    latin_text = (name + " " + props)
    latin_text = latin_text.replace("Н", "H").replace("А", "A").replace("Е", "E") \
                            .replace("О", "O").replace("Р", "P").replace("С", "C") \
                            .replace("Х", "X").replace("У", "Y").replace("В", "B")
    latin_text = latin_text.lower()

    if any(kw in text for kw in _HARDWARE_KEYWORDS):
        return True

    account_phrases = (
        # Составные фразы — однозначно аккаунт
        "общий аккаунт", "общий доступ", "аренда аккаунта", "продажа аккаунта",
        "steam аккаунт", "аккаунт steam", "account steam", "steam account",
        "без смены данных", "без смены пароля", "без смены почты",
        "смена данных", "смена пароля",
        "выданными данными", "без гарантии", "запустите один раз",
        # Технические признаки shared-доступа
        "оффлайн", "офлайн", "offline", "shared", "family sharing",
        "совместный доступ", "складчина",
        # Логин/пароль
        "логин:", "логин/пароль", "login:", "login/password",
        # Steam Guard
        "steam guard", "steamguard",
        # QR
        "qr код", "qr-код", "куар",
        # Прокат/аренда
        "аренда", "прокат", "rent ",
    )
    if any(phrase in text for phrase in account_phrases):
        return True

    services = (
        "буст", "boost", "прокачка", "leveling", "помощь", "услуг",
        "прохождение", "тренировка", "coaching", "ранг", "mmr",
    )
    if any(kw in text for kw in services):
        return True

    if any(kw in text for kw in ("кряк", "таблетка", "эмулятор", "эмул", "пиратка")):
        return True

    # Общие консольные аккаунты (П1, П2, П3 / P1, P2, P3)
    if re.search(r'(?:\b|[\(\[])(?:п[123]|p[123])(?:\b|[\]\)])', text):
        return True

    # DLC, дополнения
    if re.search(r'\bdlc\b|season pass|\bexpansion\b', text):
        return True

    # Внутриигровые предметы и валюта
    if any(kw in text for kw in ("сфер", "валют", "монет", " orb", "gems", "in-game", "ingame", " жетон",
                                  "зели", " мана", " маны", "зелье", "поинт", " руны", " rune")):
        return True

    # Чит/взлом — включая кириллические гомоглифы (Нack → hack)
    if any(kw in latin_text for kw in ("hack", "cheat", "cheats", "hook", "aimbot", "wallhack")):
        return True

    # Подписки по времени: "1 месяц", "7 дней", "30 дней" и т.п.
    if re.search(r"\d+\s*(месяц|месяца|месяцев|день|дн[её]й|дня|week|weeks)\b", text):
        return True

    if re.search(r"ключ.*аккаунт|аккаунт.*ключ", text):
        return True

    return False


def clean_game_name_for_search(name: str) -> str:
    """Очищает название игры от мусора, годов в скобках и сбитой кодировки."""
    clean = name.replace("тАЩ", "'").replace("тАФ", " ").replace("тАУ", " ")
    clean = re.sub(r"\(.*?\)|\[.*?\]", "", clean)
    clean = re.sub(r"[™®©]", "", clean)
    clean = clean.replace(":", " ").replace("-", " ").replace("–", " ").replace("—", " ").replace(",", " ")
    clean = clean.replace("’", "'").replace("`", "'").replace("‘", "'")
    return " ".join(clean.split()).strip()


def matches_game_name(lot_name: str, db_game_name: str, strict: bool = True) -> bool:
    """
    Умный матчинг: прощает маркетинговые слова ("The", "Edition", "Remastered"),
    но отклоняет лоты, у которых есть значимые слова-отличители (New, цифра части, DLC, сиквелы),
    которых нет в запросе.
    """
    stop_words = {
        "the", "of", "and", "a", "an", "in", "for", "with",
        "и", "в", "для", "на", "с", "со", "по", "от",
        "edition", "game", "year", "goty",
        "remastered", "director's", "cut", "special", "definitive", "hd", "collection",
        "enhanced", "anniversary", "extended", "standard", "standart", "базовое", "базовая",
        "базовый", "версия", "version", "издание", "издания",
    }
    noise_words = {
        "steam", "pc", "пк", "стим", "drm", "key", "ключ", "ключи", "cdkey", "cd", "code", "код", "коды",
        "gift", "гифт", "подарок", "подарком", "подарки",
        "epic", "egs", "gog", "гог", "xbox", "xsx", "xss", "xone",
        "playstation", "ps4", "ps5", "psn", "sony", "ubisoft", "uplay",
        "origin", "ea", "blizzard", "battlenet", "microsoft", "nintendo", "switch",
        "global", "region", "free", "regionfree", "row", "worldwide",
        "ru", "cis", "tr", "kz", "ar", "ua", "eu", "cn", "latam", "снг", "мир", "все", "страны",
        "россия", "рф", "рб", "беларусь", "казахстан", "кз", "украина", "укр", "турция",
        "аргентина", "европа", "europe", "asia", "без", "весь", "вся", "всей", "gl", "ww",
        "автодоставка", "автовыдача", "авто", "мгновенно", "моментально", "fast", "быстро",
        "лицензия", "лицензионный", "лицензионная", "digital", "цифровой", "электронный",
        "bundle", "deluxe", "ultimate", "complete", "gold", "platinum", "silver", "premium",
        "выбор", "онлайн", "online", "24/7", "24", "7", "0", "предзаказ", "preorder", "pre-order",
        "bonus", "бонус", "бонусы", "activation", "активация", "доставка", "delivery",
        "скидка", "скидки", "акция", "распродажа", "sale", "discount", "cheap", "дешево",
        "гарантия", "надежно", "проверено", "комиссия", "комиссией",
    }

    clean_query = clean_game_name_for_search(db_game_name).lower()
    clean_name = clean_game_name_for_search(lot_name).lower()

    query_words = set(re.findall(r'[\w]+', clean_query)) - stop_words
    name_words = set(re.findall(r'[\w]+', clean_name))

    if not query_words:
        query_words = set(re.findall(r'[\w]+', clean_query))

    if len(query_words) == 1:
        word = list(query_words)[0]
        if word not in name_words:
            return False
        # Для однословных запросов тоже проверяем лишние значимые слова
        significant_extra = (name_words - query_words) - stop_words - noise_words
        query_digits = {w for w in query_words if w.isdigit()}
        extra_digits = {w for w in significant_extra if w.isdigit()}
        if extra_digits - query_digits:
            return False
        if "new" in significant_extra and "new" not in query_words:
            return False
        if strict and significant_extra:
            return False
        return True

    if not query_words.issubset(name_words):
        return False

    dash_match = re.search(r'\s*[–—]\s*(.+)$', lot_name)
    if dash_match:
        subtitle = clean_game_name_for_search(dash_match.group(1)).lower()
        subtitle_words = set(re.findall(r'[\w]+', subtitle)) - stop_words - noise_words - query_words
        if subtitle_words:
            return False

    if ":" not in db_game_name:
        colon_match = re.search(r':\s*(.+?)(?:\s*[\|\(]|$)', lot_name)
        if colon_match:
            after_colon = clean_game_name_for_search(colon_match.group(1)).lower()
            after_words = set(re.findall(r'[\w]+', after_colon)) - stop_words - noise_words - query_words
            if after_words:
                return False

    significant_extra = (name_words - query_words) - stop_words - noise_words
    query_digits = {w for w in query_words if w.isdigit()}
    extra_digits = {w for w in significant_extra if w.isdigit()}
    if extra_digits - query_digits:
        return False
    if "new" in significant_extra and "new" not in query_words:
        return False
    if strict and significant_extra:
        return False

    return True


def detect_region(text: str) -> str:
    t = text.lower()

    # Проверяем явное отрицание / исключение РФ или России
    # Примеры: "кроме РФ", "без РФ", "не РФ", "кроме России", "не для РФ", "не для России", "нельзя активировать в РФ", "not for ru", "no ru"
    is_ru_excluded = bool(re.search(
        r"(?:кроме|без|не\s+(?:для|в|работает\s+в|активируется\s+в)?|not\s+(?:for|in)?|no|excl(?:ude[ds]?|\.)?|запрещ\w*\s+в)\s*"
        r"(?:активировать\s+)?(?:в\s+|для\s+)?"
        r"(?:рф|ru|росси\w*|rf)\b",
        t
    ))

    # Очищаем отрицательные упоминания, чтобы они не триггерили поиск региона
    t_clean = re.sub(
        r"(?:нельзя|запрещ\w*|кроме|не\s+(?:для|в)?|без|not\s+(?:for|in)?|no|excl\w*)\s+(?:активировать\s+)?(?:в\s+|для\s+)?(?:ru|рф|росси\w*|cis|снг|rf|рб|by|беларус\w*)\b",
        "",
        t
    )

    # Если исключена РФ, но указан СНГ / CIS / страны СНГ -> это CIS
    if is_ru_excluded and re.search(r"\b(cis|снг)\b", t):
        return "CIS"

    if re.search(r"(снг\s*без|cis\s*excl|без\s*рф|кроме\s*рф|кроме\s*росси|без\s*росси|не\s*рф)", t):
        return "CIS"

    # Global / Весь мир
    if re.search(r"\b(global|region free|весь мир|глобал|row|any country|all regions?|все регионы|все страны|выбор региона|worldwide)\b|\bмир\b", t_clean):
        if is_ru_excluded:
            return "CIS" if re.search(r"\b(cis|снг)\b", t) else "Global"
        return "Global"

    if re.search(r"\beu\b|europe|\bевроп", t_clean) and not re.search(r"\b(ru|рф)\b|росси[яюи]?|russia", t_clean):
        return "EU"

    # RU — ТОЛЬКО если РФ НЕ исключена!
    if not is_ru_excluded and re.search(r"\b(ru|рф)\b|росси[яюи]?|russia", t_clean):
        return "RU"

    if re.search(r"\bua\b|украин|ukraine", t_clean):
        return "UA"
    if re.search(r"\b(cis|снг)\b", t_clean):
        return "CIS"
    if re.search(r"\b(tr|турция|turkey)\b", t_clean):
        return "TR"
    if re.search(r"\b(kz|казахстан|kazakhstan)\b", t_clean):
        return "KZ"
    if re.search(r"\b(ar|аргентина|argentina|latam|latin)\b|южная\s+америка|latinoamerica", t_clean):
        return "AR"
    if re.search(r"\beu\b|europe|\bевроп", t_clean):
        return "EU"
    if re.search(r"\bcn\b|china|\bкитай", t_clean):
        return "CN"
    return "Unknown"


def detect_platform(text: str, drm: str = "", shop_name: str = "") -> str:
    """
    Определяет игровую платформу лота:
    Steam, Epic Games, Xbox, PlayStation, GOG, EA App, Ubisoft, Battle.net, Other.
    """
    drm_lower = (drm or "").lower()
    if drm_lower:
        if "steam" in drm_lower:
            return "Steam"
        if any(w in drm_lower for w in ("epic", "egs")):
            return "Epic Games"
        if "gog" in drm_lower:
            return "GOG"
        if any(w in drm_lower for w in ("xbox", "microsoft")):
            return "Xbox"
        if any(w in drm_lower for w in ("playstation", "psn", "ps4", "ps5", "sony")):
            return "PlayStation"
        if any(w in drm_lower for w in ("origin", "ea app", "ea play", " ea")):
            return "EA App"
        if any(w in drm_lower for w in ("uplay", "ubisoft")):
            return "Ubisoft"
        if any(w in drm_lower for w in ("battle.net", "battlenet", "blizzard")):
            return "Battle.net"
        if "rockstar" in drm_lower:
            return "Rockstar"

    combined = f"{text} {drm} {shop_name}".lower()

    # Специфические консольные маркеры
    if re.search(r'\b(playstation|ps[45]|psn|sony)\b', combined):
        return "PlayStation"
    if re.search(r'\b(xbox|xsx|xss|xone|xb1|series\s*[sx]|microsoft\s*store|ms\s*store)\b', combined):
        return "Xbox"

    # ПК платформы
    if re.search(r'\b(epic(\s*games)?|egs)\b', combined):
        return "Epic Games"
    if re.search(r'\b(gog(\.com)?|гог)\b', combined):
        return "GOG"
    if re.search(r'\b(battle\.net|battlenet|blizzard)\b', combined):
        return "Battle.net"
    if re.search(r'\b(ea\s*app|origin)\b', combined):
        return "EA App"
    if re.search(r'\b(ubisoft(\s*connect)?|uplay)\b', combined):
        return "Ubisoft"
    if re.search(r'\b(rockstar(\s*games)?(\s*launcher)?)\b', combined):
        return "Rockstar"

    # Steam
    if re.search(r'\b(steam|стим)\b', combined):
        return "Steam"

    # По умолчанию для магазинов цифровых ключей
    s_lower = (shop_name or "").lower()
    if any(s in s_lower for s in ("steam", "steambuy", "steampay", "gabestore", "zaka")):
        return "Steam"

    return "Steam"


def parse_price(val: object) -> float | None:
    """
    Универсальный парсер цен из строк/чисел для всех магазинов.
    Поддерживает:
    - Числа (int, float)
    - Форматы с пробелами/неразрывными пробелами: '1 290', '1\\xa0291 ₽'
    - Копейки через запятую или точку: '2 999,50 ₽', '1290.50'
    - HTML-теги и валютные суффиксы: '<span class="rub">р.</span>', '1295 <i class="rouble">c</i>'
    - Зачеркнутые цены: игнорирует старые цены внутри <s>...</s>
    - Метки отсутствия в наличии: -2, '—', 'СКОРО', 'нет в наличии' -> None
    - Нули и отрицательные значения -> None
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if val > 0 and val != -2 else None

    text = str(val).strip()
    if not text:
        return None

    lower = text.lower()
    if any(stop in lower for stop in ("—", "скоро", "нет в наличии", "out of stock", "показать еще")):
        return None

    # Отрицательные числа
    if re.search(r"(?:^|[^\w])-\s*\d+", text):
        return None

    # Детектируем валюту до удаления символов
    is_usd = bool(re.search(r"(\$|\busd\b)", text, re.IGNORECASE))
    is_eur = bool(re.search(r"(€|\beur\b)", text, re.IGNORECASE))
    is_kzt = bool(re.search(r"(₸|\bkzt\b)", text, re.IGNORECASE))

    # Удаляем зачеркнутые цены (старые цены): <s>...</s>, <del>...</del>, <strike>...</strike>
    text = re.sub(r"<(s|del|strike)>.*?</\1>", "", text, flags=re.IGNORECASE)
    # Удаляем HTML-теги
    text = re.sub(r"<[^>]+>", " ", text)
    # Нормализуем неразрывные пробелы
    text = text.replace("\xa0", " ").strip()

    if not text:
        return None

    # Ищем блок с ценой (цифры, возможные разделители)
    m = re.search(r"(\d[\d\s.,]*\d|\d)", text)
    if not m:
        return None

    num_str = m.group(1).replace(" ", "")

    # Если есть и точка, и запятая: '1,290.50' или '1.290,50'
    if "." in num_str and "," in num_str:
        if num_str.rfind(",") > num_str.rfind("."):
            num_str = num_str.replace(".", "").replace(",", ".")
        else:
            num_str = num_str.replace(",", "")
    elif "," in num_str:
        parts = num_str.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            num_str = f"{parts[0]}.{parts[1]}"
        else:
            num_str = num_str.replace(",", "")
    elif "." in num_str:
        parts = num_str.split(".")
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            pass
        else:
            num_str = num_str.replace(".", "")

    try:
        price = float(num_str)
        if price <= 0:
            return None
        if is_usd:
            price *= 100.0
        elif is_eur:
            price *= 108.0
        elif is_kzt:
            price *= 0.20
        # Отсекаем маркетплейс-заглушки отсутствия товара (99 999 ₽ и т.д.)
        if price >= 80_000:
            return None
        return round(price, 2)
    except ValueError:
        return None


def is_reliable_seller_funpay(lot_soup, min_reviews: int = 20) -> tuple[bool, bool]:
    """
    Проверяет надежность продавца на FunPay:
    - min_reviews: минимальное количество отзывов (по умолчанию >= 20)
    - rating: исключает рейтинг 1, 2, 3 звезды
    - online: определяет статус онлайн (data-online="1")
    Возвращает (is_trusted, is_online).
    """
    is_online = lot_soup.get("data-online") == "1"

    user_block = lot_soup.find(class_="tc-user")
    if not user_block:
        return True, is_online

    # Количество отзывов
    rev_el = user_block.find(class_="rating-mini-count")
    rev_text = rev_el.get_text(strip=True) if rev_el else "0"
    rev_cnt = int(rev_text) if rev_text.isdigit() else 0
    if rev_cnt < min_reviews:
        return False, is_online

    # Оценка (звёзды)
    stars_el = user_block.find(class_="rating-stars")
    if stars_el:
        classes = stars_el.get("class", [])
        if any(cls in ("rating-1", "rating-2", "rating-3") for cls in classes):
            return False, is_online

    return True, is_online


def is_reliable_seller_ggsel(
    item: dict,
    seller_info: dict | None = None,
    min_sales: int = 50,
    min_rating: float = 4.75,
    min_seller_sales: int = 100,
    min_seller_reviews: int = 15,
    max_bad_ratio: float = 0.06,
    min_reg_days: int = 14,
) -> bool:
    """
    Проверяет надежность продавца на GGSEL с защитой от скама и продавцов-однодневок:
    1. Если есть seller_info (детальная статистика аккаунта продавца):
       - total_sales: общие продажи продавца >= min_seller_sales (по умолчанию >= 100)
       - good_reviews: количество положительных отзывов >= min_seller_reviews (по умолчанию >= 15)
       - rating: общий рейтинг продавца >= min_rating (по умолчанию >= 4.75)
       - bad_ratio: доля отрицательных отзывов <= max_bad_ratio (по умолчанию <= 6%)
       - reg_days: возраст аккаунта продавца >= min_reg_days (по умолчанию >= 14 дней)
    2. Fallback (если seller_info недоступен):
       - cnt_sell: продажи лота >= min_sales (по умолчанию >= 50)
       - rating: рейтинг >= min_rating (по умолчанию >= 4.75)
    """
    if seller_info:
        total_sales = int(seller_info.get("total_sales") or 0)
        good_reviews = int(seller_info.get("good_reviews") or 0)
        bad_reviews = int(seller_info.get("bad_reviews") or 0)
        rating = float(seller_info.get("rating") or 0.0)
        registered = seller_info.get("registered")

        if total_sales < min_seller_sales:
            return False
        if good_reviews < min_seller_reviews:
            return False
        if rating < min_rating:
            return False

        tot_rev = good_reviews + bad_reviews
        if tot_rev > 0 and (bad_reviews / tot_rev) > max_bad_ratio:
            return False

        if registered and min_reg_days > 0:
            try:
                date_str = str(registered)[:10]
                reg_dt = datetime.strptime(date_str, "%Y-%m-%d")
                age_days = (datetime.utcnow() - reg_dt).days
                if age_days < min_reg_days:
                    return False
            except Exception:
                pass

        return True

    # Fallback на данные лота (если статистика продавца не получена)
    cnt_sell = item.get("cnt_sell")
    rating = item.get("rating")
    if cnt_sell is None and rating is None:
        return False

    sales = int(cnt_sell or 0)
    score = float(rating or 0.0)

    if sales < min_sales:
        return False
    if score < min_rating:
        return False
    return True


def is_reliable_seller_plati(
    item: dict, min_sales: int = 25, min_positive_ratio: float = 0.95
) -> bool:
    """
    Проверяет надежность продавца на Plati.market:
    - numsold: количество продаж товара (по умолчанию >= 25)
    - count_positiveresponses / count_negativeresponses: процент положительных отзывов >= 95%
    """
    numsold = item.get("numsold")
    if numsold is None:
        return False

    sales = int(numsold or 0)
    if sales < min_sales:
        return False

    pos = int(item.get("count_positiveresponses") or 0)
    neg = int(item.get("count_negativeresponses") or 0)
    total_reviews = pos + neg
    if total_reviews > 0:
        if (pos / total_reviews) < min_positive_ratio:
            return False

    return True

