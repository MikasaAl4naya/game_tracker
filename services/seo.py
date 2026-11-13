import html
import json
import os
import re

_cached_html: str | None = None
_last_mtime: float = 0.0

SEO_MARKER_START = "<!-- SEO_META_BLOCK_START -->"
SEO_MARKER_END = "<!-- SEO_META_BLOCK_END -->"


def generate_seo_meta_tags(
    game_name: str | None = None,
    min_price: float | None = None,
    offer_count: int | None = None,
    steam_appid: int | None = None,
    page_url: str = "http://localhost:8080/",
    custom_title: str | None = None,
    custom_description: str | None = None,
) -> str:
    """Генерирует динамические мета-теги, OpenGraph и Schema.org разметку."""
    if custom_title:
        title = custom_title
        description = custom_description or "Сравнение сервисов и цен на LootoZavr."
        image_url = "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1200&q=80"
        tags = [
            f"<title>{title}</title>",
            f'<meta name="description" content="{description}">',
            f'<link rel="canonical" href="{page_url}">',
            f'<meta property="og:type" content="website">',
            f'<meta property="og:title" content="{title}">',
            f'<meta property="og:description" content="{description}">',
            f'<meta property="og:url" content="{page_url}">',
            f'<meta property="og:image" content="{image_url}">',
            f'<meta property="og:site_name" content="LootoZavr">',
            f'<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:title" content="{title}">',
            f'<meta name="twitter:description" content="{description}">',
            f'<meta name="twitter:image" content="{image_url}">',
        ]
        return "\n    " + "\n    ".join(tags)

    if game_name:
        escaped_name = html.escape(game_name)
        min_price_str = f"от {int(min_price):,} ₽".replace(",", " ") if min_price else "по лучшей цене"
        count_str = f"в {offer_count} магазинах" if offer_count else "в проверенных магазинах"

        title = f"{escaped_name} — Купить ключ дешево {min_price_str} | LootoZavr"
        description = (
            f"Сравнение цен на цифровой ключ {escaped_name} {min_price_str} {count_str}. "
            f"Цены в Steam, Plati, Steambuy, Steampay, GGSEL, Zaka-Zaka, GabeStore, Gamerilla, GamersBase. Без аккаунтов и скама."
        )
        image_url = (
            f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{steam_appid}/header.jpg"
            if steam_appid
            else "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1200&q=80"
        )

        schema_data = {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": game_name,
            "image": image_url,
            "description": f"Цифровой ключ {game_name} для ПК",
            "brand": {"@type": "Brand", "name": "Steam"},
        }

        if min_price and offer_count:
            schema_data["offers"] = {
                "@type": "AggregateOffer",
                "priceCurrency": "RUB",
                "lowPrice": float(min_price),
                "offerCount": int(offer_count),
                "url": page_url,
            }

        tags = [
            f"<title>{title}</title>",
            f'<meta name="description" content="{description}">',
            f'<link rel="canonical" href="{page_url}">',
            # OpenGraph
            f'<meta property="og:type" content="website">',
            f'<meta property="og:title" content="{title}">',
            f'<meta property="og:description" content="{description}">',
            f'<meta property="og:url" content="{page_url}">',
            f'<meta property="og:image" content="{image_url}">',
            f'<meta property="og:site_name" content="LootoZavr">',
            # Twitter
            f'<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:title" content="{title}">',
            f'<meta name="twitter:description" content="{description}">',
            f'<meta name="twitter:image" content="{image_url}">',
            # Schema.org JSON-LD
            f'<script type="application/ld+json">{json.dumps(schema_data, ensure_ascii=False)}</script>',
        ]
    else:
        title = "LootoZavr — Агрегатор цен на игры Steam | Сравнение предложений и скидки"
        description = (
            "LootoZavr: умный агрегатор цен на ключи к играм Steam. Сравниваем предложения "
            "Plati, Steambuy, Steampay, GGSEL, Zaka-Zaka, GabeStore, Gamerilla, GamersBase с официальными региональными ценами Steam. "
            "Только реальные ключи, защита от скама и история цен."
        )
        image_url = "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1200&q=80"

        tags = [
            f"<title>{title}</title>",
            f'<meta name="description" content="{description}">',
            f'<link rel="canonical" href="{page_url}">',
            f'<meta property="og:type" content="website">',
            f'<meta property="og:title" content="{title}">',
            f'<meta property="og:description" content="{description}">',
            f'<meta property="og:url" content="{page_url}">',
            f'<meta property="og:image" content="{image_url}">',
            f'<meta property="og:site_name" content="LootoZavr">',
            f'<meta name="twitter:card" content="summary_large_image">',
        ]

    return "\n    " + "\n    ".join(tags)


def render_html_with_seo(
    template_path: str = "templates/index.html",
    game_name: str | None = None,
    min_price: float | None = None,
    offer_count: int | None = None,
    steam_appid: int | None = None,
    page_url: str = "http://localhost:8080/",
    custom_title: str | None = None,
    custom_description: str | None = None,
) -> str:
    """Загружает HTML-шаблон и подставляет кастомные SEO-теги."""
    global _cached_html, _last_mtime

    try:
        current_mtime = os.path.getmtime(template_path)
        if _cached_html is None or current_mtime > _last_mtime:
            with open(template_path, "r", encoding="utf-8") as f:
                _cached_html = f.read()
            _last_mtime = current_mtime
    except Exception:
        if _cached_html is None:
            return "<html><body>Server Error</body></html>"

    meta_tags = generate_seo_meta_tags(
        game_name=game_name,
        min_price=min_price,
        offer_count=offer_count,
        steam_appid=steam_appid,
        page_url=page_url,
        custom_title=custom_title,
        custom_description=custom_description,
    )

    pattern = re.compile(
        rf"{re.escape(SEO_MARKER_START)}.*?{re.escape(SEO_MARKER_END)}",
        re.DOTALL,
    )

    if pattern.search(_cached_html):
        return pattern.sub(f"{SEO_MARKER_START}{meta_tags}\n    {SEO_MARKER_END}", _cached_html)
    else:
        # Если маркеров нет, заменяем <title>...</title>
        return re.sub(r"<title>.*?</title>", meta_tags, _cached_html, count=1)
