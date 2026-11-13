import logging
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database import SyncSessionLocal
from models import DonateGame, DonatePackage, DonateOffer

logger = logging.getLogger(__name__)

# Полный каталог популярных игр с реальными официальными пакетами и актуальными ценами
DONATE_CATALOG_DATA = [
    {
        "slug": "genshin-impact",
        "name": "Genshin Impact",
        "publisher": "HoYoverse",
        "icon_url": "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?auto=format&fit=crop&w=120&q=80",
        "banner_url": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "Кристаллы сотворения",
        "id_type": "UID + Сервер",
        "is_popular": True,
        "sort_order": 1,
        "packages": [
            {
                "package_type": "subscription",
                "name": "Благословение полой луны 🌙",
                "amount": 30,
                "bonus": 2700,
                "icon": "fa-solid fa-moon",
                "sort_order": 1,
                "offers": [
                    {
                        "shop_name": "PlayerOK",
                        "price": 419.0,
                        "original_price": 499.0,
                        "delivery_type": "uid",
                        "delivery_time": "3-5 мин",
                        "payment_methods": "СБП, Карты РФ, T-Pay",
                        "rating": 4.9,
                        "reviews_count": 28400,
                        "promo_code": "GAMEDEALS",
                        "promo_discount": "0% комиссия СБП",
                        "url": "https://playerok.com",
                    },
                    {
                        "shop_name": "Kupikod",
                        "price": 437.0,
                        "original_price": 499.0,
                        "delivery_type": "uid",
                        "delivery_time": "1-3 мин",
                        "payment_methods": "СБП, Карты РФ, SberPay",
                        "rating": 4.95,
                        "reviews_count": 52100,
                        "promo_code": "GAMEDEALS",
                        "promo_discount": "-5% скидка",
                        "url": "https://kupikod.com/gold/genshin",
                    },
                    {
                        "shop_name": "LootBar",
                        "price": 442.0,
                        "original_price": 499.0,
                        "delivery_type": "uid",
                        "delivery_time": "2-5 мин",
                        "payment_methods": "СБП, Карты МИР",
                        "rating": 4.88,
                        "reviews_count": 18900,
                        "promo_code": "GAMEDEALS",
                        "promo_discount": "-3% кэшбэк",
                        "url": "https://lootbar.gg",
                    },
                    {
                        "shop_name": "Donatov.net",
                        "price": 448.0,
                        "original_price": 499.0,
                        "delivery_type": "uid",
                        "delivery_time": "моментально",
                        "payment_methods": "СБП, Карты РФ, T-Pay",
                        "rating": 4.92,
                        "reviews_count": 13090,
                        "promo_code": "GAMEDEALS",
                        "promo_discount": "-5% купон",
                        "url": "https://donatov.net/genshin-impact-primogems",
                    },
                    {
                        "shop_name": "FunPay",
                        "price": 379.0,
                        "original_price": 499.0,
                        "delivery_type": "login",
                        "delivery_time": "5-15 мин",
                        "payment_methods": "СБП, Карты, ЮMoney",
                        "rating": 4.85,
                        "reviews_count": 94000,
                        "promo_code": None,
                        "promo_discount": None,
                        "url": "https://funpay.com",
                    },
                ],
            },
            {
                "package_type": "pass",
                "name": "Боевой пропуск (Жемчужный гимн)",
                "amount": 1,
                "bonus": 0,
                "icon": "fa-solid fa-scroll",
                "sort_order": 2,
                "offers": [
                    {
                        "shop_name": "PlayerOK",
                        "price": 849.0,
                        "original_price": 999.0,
                        "delivery_type": "uid",
                        "delivery_time": "3-5 мин",
                        "payment_methods": "СБП, Карты РФ",
                        "rating": 4.9,
                        "reviews_count": 28400,
                        "promo_code": "GAMEDEALS",
                        "promo_discount": "0% комиссия",
                        "url": "https://playerok.com",
                    },
                    {
                        "shop_name": "Kupikod",
                        "price": 875.0,
                        "original_price": 999.0,
                        "delivery_type": "uid",
                        "delivery_time": "1-3 мин",
                        "payment_methods": "СБП, Карты РФ",
                        "rating": 4.95,
                        "reviews_count": 52100,
                        "promo_code": "GAMEDEALS",
                        "promo_discount": "-5% скидка",
                        "url": "https://kupikod.com/gold/genshin",
                    },
                    {
                        "shop_name": "Donatov.net",
                        "price": 890.0,
                        "original_price": 999.0,
                        "delivery_type": "uid",
                        "delivery_time": "моментально",
                        "payment_methods": "СБП, Карты РФ",
                        "rating": 4.92,
                        "reviews_count": 13090,
                        "promo_code": "GAMEDEALS",
                        "promo_discount": "-5% купон",
                        "url": "https://donatov.net/genshin-impact-primogems",
                    },
                    {
                        "shop_name": "FunPay",
                        "price": 760.0,
                        "original_price": 999.0,
                        "delivery_type": "login",
                        "delivery_time": "10-20 мин",
                        "payment_methods": "СБП, Карты",
                        "rating": 4.85,
                        "reviews_count": 94000,
                        "promo_code": None,
                        "promo_discount": None,
                        "url": "https://funpay.com",
                    },
                ],
            },
            {
                "package_type": "currency",
                "name": "60 кристаллов сотворения 💎",
                "amount": 60,
                "bonus": 60,
                "icon": "fa-solid fa-gem",
                "sort_order": 3,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 79.0, "original_price": 99.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 81.0, "original_price": 99.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/genshin"},
                    {"shop_name": "Donatov.net", "price": 85.0, "original_price": 99.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/genshin-impact-primogems"},
                ],
            },
            {
                "package_type": "currency",
                "name": "300 + 30 кристаллов 💎",
                "amount": 300,
                "bonus": 30,
                "icon": "fa-solid fa-gem",
                "sort_order": 4,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 395.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "3-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 403.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/genshin"},
                    {"shop_name": "Donatov.net", "price": 448.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/genshin-impact-primogems"},
                ],
            },
            {
                "package_type": "currency",
                "name": "980 + 110 кристаллов 💎",
                "amount": 980,
                "bonus": 110,
                "icon": "fa-solid fa-gem",
                "sort_order": 5,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 1199.0, "original_price": 1490.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 1232.0, "original_price": 1490.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/genshin"},
                    {"shop_name": "Donatov.net", "price": 1289.0, "original_price": 1490.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/genshin-impact-primogems"},
                ],
            },
            {
                "package_type": "currency",
                "name": "1980 + 260 кристаллов 💎",
                "amount": 1980,
                "bonus": 260,
                "icon": "fa-solid fa-gem",
                "sort_order": 6,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 2640.0, "original_price": 2990.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Donatov.net", "price": 2690.0, "original_price": 2990.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/genshin-impact-primogems"},
                    {"shop_name": "Kupikod", "price": 2770.0, "original_price": 2990.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/genshin"},
                ],
            },
            {
                "package_type": "currency",
                "name": "3280 + 600 кристаллов 💎",
                "amount": 3280,
                "bonus": 600,
                "icon": "fa-solid fa-gem",
                "sort_order": 7,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 4390.0, "original_price": 4990.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Donatov.net", "price": 4490.0, "original_price": 4990.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/genshin-impact-primogems"},
                    {"shop_name": "Kupikod", "price": 4494.0, "original_price": 4990.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/genshin"},
                ],
            },
            {
                "package_type": "currency",
                "name": "6480 + 1600 кристаллов 💎",
                "amount": 6480,
                "bonus": 1600,
                "icon": "fa-solid fa-gem",
                "sort_order": 8,
                "offers": [
                    {"shop_name": "BattlePass", "price": 8390.0, "original_price": 9990.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.96, "reviews_count": 45000, "promo_code": "HLX", "promo_discount": "0% сбор", "url": "https://battlepass.ru/service/genshin"},
                    {"shop_name": "PlayerOK", "price": 8490.0, "original_price": 9990.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Donatov.net", "price": 8579.0, "original_price": 9990.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/genshin-impact-primogems"},
                    {"shop_name": "GenshinDrop", "price": 9015.0, "original_price": 9990.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты МИР", "rating": 4.94, "reviews_count": 32000, "promo_code": "GAMEDEALS", "promo_discount": "-3%", "url": "https://genshindrop.io/shop"},
                    {"shop_name": "Kupikod", "price": 9039.0, "original_price": 9990.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/genshin"},
                ],
            },
        ],
    },
    {
        "slug": "honkai-star-rail",
        "name": "Honkai: Star Rail",
        "publisher": "HoYoverse",
        "icon_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=120&q=80",
        "banner_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "Сущности древних снов",
        "id_type": "UID + Сервер",
        "is_popular": True,
        "sort_order": 2,
        "packages": [
            {
                "package_type": "subscription",
                "name": "Пропуск снабжения экспресса 🚂",
                "amount": 30,
                "bonus": 2700,
                "icon": "fa-solid fa-train",
                "sort_order": 1,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 419.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "3-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 437.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/honkai"},
                    {"shop_name": "Donatov.net", "price": 448.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/honkai-star-rail-gems"},
                ],
            },
            {
                "package_type": "pass",
                "name": "Честь безымянных (Слава безымянных)",
                "amount": 1,
                "bonus": 0,
                "icon": "fa-solid fa-award",
                "sort_order": 2,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 849.0, "original_price": 999.0, "delivery_type": "uid", "delivery_time": "3-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 875.0, "original_price": 999.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/honkai"},
                    {"shop_name": "Donatov.net", "price": 890.0, "original_price": 999.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/honkai-star-rail-gems"},
                ],
            },
            {
                "package_type": "currency",
                "name": "60 сущностей древних снов 💎",
                "amount": 60,
                "bonus": 60,
                "icon": "fa-solid fa-gem",
                "sort_order": 3,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 79.0, "original_price": 99.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 81.0, "original_price": 99.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/honkai"},
                    {"shop_name": "Donatov.net", "price": 85.0, "original_price": 99.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/honkai-star-rail-gems"},
                ],
            },
            {
                "package_type": "currency",
                "name": "980 + 110 сущностей древних снов 💎",
                "amount": 980,
                "bonus": 110,
                "icon": "fa-solid fa-gem",
                "sort_order": 4,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 1199.0, "original_price": 1490.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 1232.0, "original_price": 1490.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/honkai"},
                    {"shop_name": "Donatov.net", "price": 1289.0, "original_price": 1490.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/honkai-star-rail-gems"},
                ],
            },
            {
                "package_type": "currency",
                "name": "3280 + 600 сущностей древних снов 💎",
                "amount": 3280,
                "bonus": 600,
                "icon": "fa-solid fa-gem",
                "sort_order": 5,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 4390.0, "original_price": 4990.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Donatov.net", "price": 4490.0, "original_price": 4990.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/honkai-star-rail-gems"},
                    {"shop_name": "Kupikod", "price": 4494.0, "original_price": 4990.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/honkai"},
                ],
            },
        ],
    },
    {
        "slug": "brawl-stars",
        "name": "Brawl Stars",
        "publisher": "Supercell",
        "icon_url": "https://images.unsplash.com/photo-1563089145-599997674d42?auto=format&fit=crop&w=120&q=80",
        "banner_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "Гемы (Кристаллы)",
        "id_type": "Supercell ID",
        "is_popular": True,
        "sort_order": 3,
        "packages": [
            {
                "package_type": "pass",
                "name": "Brawl Pass ⭐",
                "amount": 1,
                "bonus": 0,
                "icon": "fa-solid fa-star",
                "sort_order": 1,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 749.0, "original_price": 899.0, "delivery_type": "uid", "delivery_time": "5 мин", "payment_methods": "СБП, Карты РФ", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 789.0, "original_price": 899.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты РФ", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/brawl-stars"},
                    {"shop_name": "Donatov.net", "price": 799.0, "original_price": 899.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты РФ", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/brawl-stars-gems"},
                ],
            },
            {
                "package_type": "pass",
                "name": "Brawl Pass Plus 👑",
                "amount": 1,
                "bonus": 0,
                "icon": "fa-solid fa-crown",
                "sort_order": 2,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 1150.0, "original_price": 1390.0, "delivery_type": "uid", "delivery_time": "5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 1190.0, "original_price": 1390.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/brawl-stars"},
                    {"shop_name": "Donatov.net", "price": 1210.0, "original_price": 1390.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/brawl-stars-gems"},
                ],
            },
            {
                "package_type": "currency",
                "name": "80 гемов 💎",
                "amount": 80,
                "bonus": 0,
                "icon": "fa-solid fa-gem",
                "sort_order": 3,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 459.0, "original_price": 549.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 479.0, "original_price": 549.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/brawl-stars"},
                    {"shop_name": "Donatov.net", "price": 489.0, "original_price": 549.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/brawl-stars-gems"},
                ],
            },
            {
                "package_type": "currency",
                "name": "170 гемов 💎",
                "amount": 170,
                "bonus": 0,
                "icon": "fa-solid fa-gem",
                "sort_order": 4,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 929.0, "original_price": 1090.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 969.0, "original_price": 1090.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/brawl-stars"},
                    {"shop_name": "Donatov.net", "price": 989.0, "original_price": 1090.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/brawl-stars-gems"},
                ],
            },
            {
                "package_type": "currency",
                "name": "360 гемов 💎",
                "amount": 360,
                "bonus": 0,
                "icon": "fa-solid fa-gem",
                "sort_order": 5,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 1870.0, "original_price": 2190.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 1929.0, "original_price": 2190.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/brawl-stars"},
                    {"shop_name": "Donatov.net", "price": 1950.0, "original_price": 2190.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/brawl-stars-gems"},
                ],
            },
        ],
    },
    {
        "slug": "roblox",
        "name": "Roblox",
        "publisher": "Roblox Corporation",
        "icon_url": "https://images.unsplash.com/photo-1593305841991-05c297ba4575?auto=format&fit=crop&w=120&q=80",
        "banner_url": "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "Робуксы (Robux)",
        "id_type": "Никнейм (Логин)",
        "is_popular": True,
        "sort_order": 4,
        "packages": [
            {
                "package_type": "currency",
                "name": "400 Robux R$",
                "amount": 400,
                "bonus": 0,
                "icon": "fa-solid fa-cube",
                "sort_order": 1,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 520.0, "original_price": 599.0, "delivery_type": "uid", "delivery_time": "5-10 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 549.0, "original_price": 599.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/roblox"},
                    {"shop_name": "Donatov.net", "price": 560.0, "original_price": 599.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/roblox-login"},
                ],
            },
            {
                "package_type": "currency",
                "name": "800 Robux R$",
                "amount": 800,
                "bonus": 0,
                "icon": "fa-solid fa-cube",
                "sort_order": 2,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 990.0, "original_price": 1190.0, "delivery_type": "uid", "delivery_time": "5-10 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 1049.0, "original_price": 1190.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/roblox"},
                    {"shop_name": "Donatov.net", "price": 1070.0, "original_price": 1190.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/roblox-login"},
                ],
            },
            {
                "package_type": "currency",
                "name": "1700 Robux R$",
                "amount": 1700,
                "bonus": 0,
                "icon": "fa-solid fa-cube",
                "sort_order": 3,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 1990.0, "original_price": 2390.0, "delivery_type": "uid", "delivery_time": "5-10 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 2099.0, "original_price": 2390.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/roblox"},
                    {"shop_name": "Donatov.net", "price": 2150.0, "original_price": 2390.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/roblox-login"},
                ],
            },
        ],
    },
    {
        "slug": "zenless-zone-zero",
        "name": "Zenless Zone Zero",
        "publisher": "HoYoverse",
        "icon_url": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=120&q=80",
        "banner_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "Монохромы",
        "id_type": "UID + Сервер",
        "is_popular": True,
        "sort_order": 5,
        "packages": [
            {
                "package_type": "subscription",
                "name": "Интернот-подписка 📺",
                "amount": 30,
                "bonus": 2700,
                "icon": "fa-solid fa-tv",
                "sort_order": 1,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 419.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "3-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 437.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/zenless-zone-zero"},
                    {"shop_name": "Donatov.net", "price": 448.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/zenless-zone-zero"},
                ],
            },
            {
                "package_type": "pass",
                "name": "План фонда Риду (Боевой пропуск)",
                "amount": 1,
                "bonus": 0,
                "icon": "fa-solid fa-id-card",
                "sort_order": 2,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 849.0, "original_price": 999.0, "delivery_type": "uid", "delivery_time": "3-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 875.0, "original_price": 999.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/zenless-zone-zero"},
                    {"shop_name": "Donatov.net", "price": 890.0, "original_price": 999.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/zenless-zone-zero"},
                ],
            },
            {
                "package_type": "currency",
                "name": "980 + 110 монохромов 💎",
                "amount": 980,
                "bonus": 110,
                "icon": "fa-solid fa-gem",
                "sort_order": 3,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 1199.0, "original_price": 1490.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 1232.0, "original_price": 1490.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/zenless-zone-zero"},
                    {"shop_name": "Donatov.net", "price": 1289.0, "original_price": 1490.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/zenless-zone-zero"},
                ],
            },
        ],
    },
    {
        "slug": "mobile-legends",
        "name": "Mobile Legends: Bang Bang",
        "publisher": "Moonton",
        "icon_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=120&q=80",
        "banner_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "Алмазы (Diamonds)",
        "id_type": "ID + Сервер (Zone ID)",
        "is_popular": True,
        "sort_order": 6,
        "packages": [
            {
                "package_type": "pass",
                "name": "Алмазный пропуск недели (Weekly Pass) 💎",
                "amount": 1,
                "bonus": 220,
                "icon": "fa-solid fa-gem",
                "sort_order": 1,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 169.0, "original_price": 210.0, "delivery_type": "uid", "delivery_time": "2-3 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 179.0, "original_price": 210.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/mobile-legends"},
                    {"shop_name": "Donatov.net", "price": 185.0, "original_price": 210.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/mobile-legends"},
                ],
            },
            {
                "package_type": "currency",
                "name": "250 + 25 алмазов 💎",
                "amount": 250,
                "bonus": 25,
                "icon": "fa-solid fa-gem",
                "sort_order": 2,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 419.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "2-3 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 439.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/mobile-legends"},
                    {"shop_name": "Donatov.net", "price": 449.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/mobile-legends"},
                ],
            },
        ],
    },
    {
        "slug": "pubg-mobile",
        "name": "PUBG Mobile",
        "publisher": "Tencent / Krafton",
        "icon_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=120&q=80",
        "banner_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "UC (Unknown Cash)",
        "id_type": "Числовой ID персонажа",
        "is_popular": True,
        "sort_order": 7,
        "packages": [
            {
                "package_type": "currency",
                "name": "60 UC 💵",
                "amount": 60,
                "bonus": 0,
                "icon": "fa-solid fa-coins",
                "sort_order": 1,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 85.0, "original_price": 105.0, "delivery_type": "uid", "delivery_time": "2 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 89.0, "original_price": 105.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/pubg"},
                    {"shop_name": "Donatov.net", "price": 95.0, "original_price": 105.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/pubg-mobile-uc"},
                ],
            },
            {
                "package_type": "currency",
                "name": "300 + 25 UC 💵",
                "amount": 300,
                "bonus": 25,
                "icon": "fa-solid fa-coins",
                "sort_order": 2,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 419.0, "original_price": 490.0, "delivery_type": "uid", "delivery_time": "2 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 439.0, "original_price": 490.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/pubg"},
                    {"shop_name": "Donatov.net", "price": 449.0, "original_price": 490.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/pubg-mobile-uc"},
                ],
            },
            {
                "package_type": "currency",
                "name": "600 + 60 UC 💵",
                "amount": 600,
                "bonus": 60,
                "icon": "fa-solid fa-coins",
                "sort_order": 3,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 839.0, "original_price": 990.0, "delivery_type": "uid", "delivery_time": "2 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 869.0, "original_price": 990.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/pubg"},
                    {"shop_name": "Donatov.net", "price": 889.0, "original_price": 990.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/pubg-mobile-uc"},
                ],
            },
        ],
    },
    {
        "slug": "telegram-stars",
        "name": "Telegram Stars",
        "publisher": "Telegram",
        "icon_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=120&q=80",
        "banner_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "Звёзды (Stars)",
        "id_type": "@username пользователя",
        "is_popular": True,
        "sort_order": 8,
        "packages": [
            {
                "package_type": "currency",
                "name": "50 звёзд ⭐",
                "amount": 50,
                "bonus": 0,
                "icon": "fa-solid fa-star",
                "sort_order": 1,
                "offers": [
                    {"shop_name": "FunPay", "price": 89.0, "original_price": 115.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.85, "reviews_count": 94000, "promo_code": None, "promo_discount": None, "url": "https://funpay.com"},
                    {"shop_name": "PlayerOK", "price": 95.0, "original_price": 115.0, "delivery_type": "uid", "delivery_time": "2 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 99.0, "original_price": 115.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com"},
                ],
            },
            {
                "package_type": "currency",
                "name": "250 звёзд ⭐",
                "amount": 250,
                "bonus": 0,
                "icon": "fa-solid fa-star",
                "sort_order": 2,
                "offers": [
                    {"shop_name": "FunPay", "price": 445.0, "original_price": 540.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.85, "reviews_count": 94000, "promo_code": None, "promo_discount": None, "url": "https://funpay.com"},
                    {"shop_name": "PlayerOK", "price": 465.0, "original_price": 540.0, "delivery_type": "uid", "delivery_time": "2 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 479.0, "original_price": 540.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com"},
                ],
            },
            {
                "package_type": "currency",
                "name": "500 звёзд ⭐",
                "amount": 500,
                "bonus": 0,
                "icon": "fa-solid fa-star",
                "sort_order": 3,
                "offers": [
                    {"shop_name": "FunPay", "price": 880.0, "original_price": 1050.0, "delivery_type": "uid", "delivery_time": "3 мин", "payment_methods": "СБП, Карты", "rating": 4.85, "reviews_count": 94000, "promo_code": None, "promo_discount": None, "url": "https://funpay.com"},
                    {"shop_name": "PlayerOK", "price": 920.0, "original_price": 1050.0, "delivery_type": "uid", "delivery_time": "2 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 949.0, "original_price": 1050.0, "delivery_type": "uid", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com"},
                ],
            },
        ],
    },
    {
        "slug": "valorant",
        "name": "Valorant",
        "publisher": "Riot Games",
        "icon_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=120&q=80",
        "banner_url": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "Valorant Points (VP)",
        "id_type": "Riot ID (Код активации)",
        "is_popular": True,
        "sort_order": 9,
        "packages": [
            {
                "package_type": "currency",
                "name": "475 Valorant Points (VP) 🎯",
                "amount": 475,
                "bonus": 0,
                "icon": "fa-solid fa-crosshairs",
                "sort_order": 1,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 460.0, "original_price": 520.0, "delivery_type": "code", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "GGSEL", "price": 470.0, "original_price": 520.0, "delivery_type": "code", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.88, "reviews_count": 42000, "promo_code": None, "promo_discount": None, "url": "https://ggsel.net"},
                    {"shop_name": "Kupikod", "price": 489.0, "original_price": 520.0, "delivery_type": "code", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/valorant"},
                    {"shop_name": "Donatov.net", "price": 499.0, "original_price": 520.0, "delivery_type": "code", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/valorant-point-code"},
                ],
            },
            {
                "package_type": "currency",
                "name": "1000 Valorant Points (VP) 🎯",
                "amount": 1000,
                "bonus": 0,
                "icon": "fa-solid fa-crosshairs",
                "sort_order": 2,
                "offers": [
                    {"shop_name": "PlayerOK", "price": 930.0, "original_price": 1050.0, "delivery_type": "code", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "GGSEL", "price": 940.0, "original_price": 1050.0, "delivery_type": "code", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.88, "reviews_count": 42000, "promo_code": None, "promo_discount": None, "url": "https://ggsel.net"},
                    {"shop_name": "Kupikod", "price": 979.0, "original_price": 1050.0, "delivery_type": "code", "delivery_time": "1 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold/valorant"},
                    {"shop_name": "Donatov.net", "price": 999.0, "original_price": 1050.0, "delivery_type": "code", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/valorant-point-code"},
                ],
            },
        ],
    },
    {
        "slug": "wuthering-waves",
        "name": "Wuthering Waves",
        "publisher": "Kuro Games",
        "icon_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=120&q=80",
        "banner_url": "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "Луниты",
        "id_type": "UID + Сервер",
        "is_popular": True,
        "sort_order": 10,
        "packages": [
            {
                "package_type": "subscription",
                "name": "Лунная подписка (30 дней) 🌙",
                "amount": 30,
                "bonus": 2700,
                "icon": "fa-solid fa-moon",
                "sort_order": 1,
                "offers": [
                    {"shop_name": "BattlePass", "price": 410.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты РФ", "rating": 4.96, "reviews_count": 45000, "promo_code": "HLX", "promo_discount": "0% сбор", "url": "https://battlepass.ru/service/wuthering_waves"},
                    {"shop_name": "Donatov.net", "price": 418.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/wuthering-waves-uid"},
                    {"shop_name": "HornyBox", "price": 422.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 22000, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://hornybox.com"},
                    {"shop_name": "LDShop", "price": 425.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "2-4 мин", "payment_methods": "СБП, МИР", "rating": 4.88, "reviews_count": 31000, "promo_code": "GAMEDEALS", "promo_discount": "Кэшбэк 10%", "url": "https://ldshop.gg/ru"},
                    {"shop_name": "PlayerOK", "price": 429.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "3-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 445.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold"},
                ],
            },
            {
                "package_type": "pass",
                "name": "Инсайдерский подкаст (BP) 📜",
                "amount": 1,
                "bonus": 0,
                "icon": "fa-solid fa-scroll",
                "sort_order": 2,
                "offers": [
                    {"shop_name": "BattlePass", "price": 820.0, "original_price": 999.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.96, "reviews_count": 45000, "promo_code": "HLX", "promo_discount": "0% сбор", "url": "https://battlepass.ru/service/wuthering_waves"},
                    {"shop_name": "Donatov.net", "price": 839.0, "original_price": 999.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/wuthering-waves-uid"},
                    {"shop_name": "HornyBox", "price": 845.0, "original_price": 999.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 22000, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://hornybox.com"},
                    {"shop_name": "PlayerOK", "price": 859.0, "original_price": 999.0, "delivery_type": "uid", "delivery_time": "3-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 889.0, "original_price": 999.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold"},
                ],
            },
            {
                "package_type": "currency",
                "name": "300 + 30 Лунитов 💎",
                "amount": 300,
                "bonus": 30,
                "icon": "fa-solid fa-gem",
                "sort_order": 3,
                "offers": [
                    {"shop_name": "BattlePass", "price": 389.0, "original_price": 450.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.96, "reviews_count": 45000, "promo_code": "HLX", "promo_discount": "0% сбор", "url": "https://battlepass.ru/service/wuthering_waves"},
                    {"shop_name": "Donatov.net", "price": 395.0, "original_price": 450.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/wuthering-waves-uid"},
                    {"shop_name": "HornyBox", "price": 399.0, "original_price": 450.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 22000, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://hornybox.com"},
                    {"shop_name": "PlayerOK", "price": 410.0, "original_price": 450.0, "delivery_type": "uid", "delivery_time": "3-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                ],
            },
            {
                "package_type": "currency",
                "name": "980 + 110 Лунитов 💎",
                "amount": 980,
                "bonus": 110,
                "icon": "fa-solid fa-gem",
                "sort_order": 4,
                "offers": [
                    {"shop_name": "BattlePass", "price": 1170.0, "original_price": 1350.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.96, "reviews_count": 45000, "promo_code": "HLX", "promo_discount": "0% сбор", "url": "https://battlepass.ru/service/wuthering_waves"},
                    {"shop_name": "Donatov.net", "price": 1190.0, "original_price": 1350.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/wuthering-waves-uid"},
                    {"shop_name": "LDShop", "price": 1199.0, "original_price": 1350.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, МИР", "rating": 4.88, "reviews_count": 31000, "promo_code": "GAMEDEALS", "promo_discount": "Кэшбэк 10%", "url": "https://ldshop.gg/ru"},
                    {"shop_name": "Kupikod", "price": 1250.0, "original_price": 1350.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold"},
                ],
            },
            {
                "package_type": "currency",
                "name": "1980 + 260 Лунитов 💎",
                "amount": 1980,
                "bonus": 260,
                "icon": "fa-solid fa-gem",
                "sort_order": 5,
                "offers": [
                    {"shop_name": "LDShop", "price": 2380.0, "original_price": 2690.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, МИР", "rating": 4.88, "reviews_count": 31000, "promo_code": "GAMEDEALS", "promo_discount": "Кэшбэк 10%", "url": "https://ldshop.gg/ru"},
                    {"shop_name": "BattlePass", "price": 2390.0, "original_price": 2690.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.96, "reviews_count": 45000, "promo_code": "HLX", "promo_discount": "0% сбор", "url": "https://battlepass.ru/service/wuthering_waves"},
                    {"shop_name": "Donatov.net", "price": 2420.0, "original_price": 2690.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/wuthering-waves-uid"},
                    {"shop_name": "PlayerOK", "price": 2460.0, "original_price": 2690.0, "delivery_type": "uid", "delivery_time": "3-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                ],
            },
            {
                "package_type": "currency",
                "name": "6480 + 1600 Лунитов 💎",
                "amount": 6480,
                "bonus": 1600,
                "icon": "fa-solid fa-gem",
                "sort_order": 6,
                "offers": [
                    {"shop_name": "BattlePass", "price": 7790.0, "original_price": 8990.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.96, "reviews_count": 45000, "promo_code": "HLX", "promo_discount": "0% сбор", "url": "https://battlepass.ru/service/wuthering_waves"},
                    {"shop_name": "Donatov.net", "price": 7890.0, "original_price": 8990.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/wuthering-waves-uid"},
                    {"shop_name": "LDShop", "price": 7950.0, "original_price": 8990.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, МИР", "rating": 4.88, "reviews_count": 31000, "promo_code": "GAMEDEALS", "promo_discount": "Кэшбэк 10%", "url": "https://ldshop.gg/ru"},
                    {"shop_name": "Kupikod", "price": 8490.0, "original_price": 8990.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold"},
                ],
            },
        ],
    },
    {
        "slug": "standoff-2",
        "name": "Standoff 2",
        "publisher": "Axlebolt",
        "icon_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=120&q=80",
        "banner_url": "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "Золото (Gold / G)",
        "id_type": "ID игрока",
        "is_popular": True,
        "sort_order": 11,
        "packages": [
            {
                "package_type": "pass",
                "name": "Gold Pass 🎖️",
                "amount": 1,
                "bonus": 0,
                "icon": "fa-solid fa-medal",
                "sort_order": 1,
                "offers": [
                    {"shop_name": "Donatov.net", "price": 479.0, "original_price": 549.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/standoff2-golds"},
                    {"shop_name": "PlayerOK", "price": 489.0, "original_price": 549.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 499.0, "original_price": 549.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold"},
                ],
            },
            {
                "package_type": "currency",
                "name": "100 Gold 🪙",
                "amount": 100,
                "bonus": 0,
                "icon": "fa-solid fa-coins",
                "sort_order": 2,
                "offers": [
                    {"shop_name": "Donatov.net", "price": 149.0, "original_price": 179.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/standoff2-golds"},
                    {"shop_name": "PlayerOK", "price": 155.0, "original_price": 179.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 159.0, "original_price": 179.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold"},
                ],
            },
            {
                "package_type": "currency",
                "name": "500 Gold 🪙",
                "amount": 500,
                "bonus": 0,
                "icon": "fa-solid fa-coins",
                "sort_order": 3,
                "offers": [
                    {"shop_name": "Donatov.net", "price": 689.0, "original_price": 799.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/standoff2-golds"},
                    {"shop_name": "PlayerOK", "price": 699.0, "original_price": 799.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 729.0, "original_price": 799.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold"},
                ],
            },
            {
                "package_type": "currency",
                "name": "1000 Gold 🪙",
                "amount": 1000,
                "bonus": 0,
                "icon": "fa-solid fa-coins",
                "sort_order": 4,
                "offers": [
                    {"shop_name": "Donatov.net", "price": 1349.0, "original_price": 1590.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/standoff2-golds"},
                    {"shop_name": "PlayerOK", "price": 1370.0, "original_price": 1590.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 1420.0, "original_price": 1590.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold"},
                ],
            },
            {
                "package_type": "currency",
                "name": "3000 Gold 🪙",
                "amount": 3000,
                "bonus": 0,
                "icon": "fa-solid fa-coins",
                "sort_order": 5,
                "offers": [
                    {"shop_name": "Donatov.net", "price": 3890.0, "original_price": 4490.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/standoff2-golds"},
                    {"shop_name": "PlayerOK", "price": 3950.0, "original_price": 4490.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "Kupikod", "price": 4090.0, "original_price": 4490.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.95, "reviews_count": 52100, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://kupikod.com/gold"},
                ],
            },
        ],
    },
    {
        "slug": "marvel-rivals",
        "name": "Marvel Rivals",
        "publisher": "NetEase Games",
        "icon_url": "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?auto=format&fit=crop&w=120&q=80",
        "banner_url": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "Латисы (Lattices)",
        "id_type": "UID игрока",
        "is_popular": True,
        "sort_order": 12,
        "packages": [
            {
                "package_type": "pass",
                "name": "Боевой пропуск Rivals 🦸",
                "amount": 1,
                "bonus": 0,
                "icon": "fa-solid fa-shield-halved",
                "sort_order": 1,
                "offers": [
                    {"shop_name": "BattlePass", "price": 890.0, "original_price": 1050.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.96, "reviews_count": 45000, "promo_code": "HLX", "promo_discount": "0% сбор", "url": "https://battlepass.ru/service/marvel_rivals"},
                    {"shop_name": "Donatov.net", "price": 920.0, "original_price": 1050.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/marvel-rivals"},
                    {"shop_name": "PlayerOK", "price": 940.0, "original_price": 1050.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                    {"shop_name": "HornyBox", "price": 945.0, "original_price": 1050.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 22000, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://hornybox.com"},
                ],
            },
            {
                "package_type": "currency",
                "name": "500 Латисов ⚡",
                "amount": 500,
                "bonus": 0,
                "icon": "fa-solid fa-bolt",
                "sort_order": 2,
                "offers": [
                    {"shop_name": "BattlePass", "price": 463.0, "original_price": 550.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.96, "reviews_count": 45000, "promo_code": "HLX", "promo_discount": "0% сбор", "url": "https://battlepass.ru/service/marvel_rivals"},
                    {"shop_name": "Donatov.net", "price": 489.0, "original_price": 550.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/marvel-rivals"},
                    {"shop_name": "PlayerOK", "price": 499.0, "original_price": 550.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                ],
            },
            {
                "package_type": "currency",
                "name": "1000 Латисов ⚡",
                "amount": 1000,
                "bonus": 0,
                "icon": "fa-solid fa-bolt",
                "sort_order": 3,
                "offers": [
                    {"shop_name": "BattlePass", "price": 927.0, "original_price": 1050.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.96, "reviews_count": 45000, "promo_code": "HLX", "promo_discount": "0% сбор", "url": "https://battlepass.ru/service/marvel_rivals"},
                    {"shop_name": "Donatov.net", "price": 940.0, "original_price": 1050.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/marvel-rivals"},
                    {"shop_name": "PlayerOK", "price": 960.0, "original_price": 1050.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                ],
            },
            {
                "package_type": "currency",
                "name": "2180 Латисов ⚡",
                "amount": 2180,
                "bonus": 180,
                "icon": "fa-solid fa-bolt",
                "sort_order": 4,
                "offers": [
                    {"shop_name": "BattlePass", "price": 1856.0, "original_price": 2190.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.96, "reviews_count": 45000, "promo_code": "HLX", "promo_discount": "0% сбор", "url": "https://battlepass.ru/service/marvel_rivals"},
                    {"shop_name": "Donatov.net", "price": 1940.0, "original_price": 2190.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/marvel-rivals"},
                    {"shop_name": "PlayerOK", "price": 1980.0, "original_price": 2190.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                ],
            },
            {
                "package_type": "currency",
                "name": "5600 Латисов ⚡",
                "amount": 5600,
                "bonus": 600,
                "icon": "fa-solid fa-bolt",
                "sort_order": 5,
                "offers": [
                    {"shop_name": "BattlePass", "price": 4690.0, "original_price": 5390.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.96, "reviews_count": 45000, "promo_code": "HLX", "promo_discount": "0% сбор", "url": "https://battlepass.ru/service/marvel_rivals"},
                    {"shop_name": "Donatov.net", "price": 4790.0, "original_price": 5390.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/marvel-rivals"},
                    {"shop_name": "PlayerOK", "price": 4890.0, "original_price": 5390.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                ],
            },
        ],
    },
    {
        "slug": "love-and-deepspace",
        "name": "Love and Deepspace",
        "publisher": "Infold Games",
        "icon_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=120&q=80",
        "banner_url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
        "currency_name": "Кристаллы (Crystals)",
        "id_type": "ID игрока (без пароля)",
        "is_popular": True,
        "sort_order": 13,
        "packages": [
            {
                "package_type": "subscription",
                "name": "Аурум пропуск (Aurum Pass) 💫",
                "amount": 30,
                "bonus": 3000,
                "icon": "fa-solid fa-sparkles",
                "sort_order": 1,
                "offers": [
                    {"shop_name": "BattlePass", "price": 420.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.96, "reviews_count": 45000, "promo_code": "HLX", "promo_discount": "0% сбор", "url": "https://battlepass.ru/service/lovedspace"},
                    {"shop_name": "Donatov.net", "price": 435.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/love-and-deepspace"},
                    {"shop_name": "HornyBox", "price": 439.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 22000, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://hornybox.com"},
                    {"shop_name": "PlayerOK", "price": 449.0, "original_price": 499.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                ],
            },
            {
                "package_type": "currency",
                "name": "300 + 30 Кристаллов 💎",
                "amount": 300,
                "bonus": 30,
                "icon": "fa-solid fa-gem",
                "sort_order": 2,
                "offers": [
                    {"shop_name": "BattlePass", "price": 410.0, "original_price": 480.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.96, "reviews_count": 45000, "promo_code": "HLX", "promo_discount": "0% сбор", "url": "https://battlepass.ru/service/lovedspace"},
                    {"shop_name": "Donatov.net", "price": 420.0, "original_price": 480.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/love-and-deepspace"},
                    {"shop_name": "PlayerOK", "price": 435.0, "original_price": 480.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                ],
            },
            {
                "package_type": "currency",
                "name": "980 + 110 Кристаллов 💎",
                "amount": 980,
                "bonus": 110,
                "icon": "fa-solid fa-gem",
                "sort_order": 3,
                "offers": [
                    {"shop_name": "BattlePass", "price": 1220.0, "original_price": 1390.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.96, "reviews_count": 45000, "promo_code": "HLX", "promo_discount": "0% сбор", "url": "https://battlepass.ru/service/lovedspace"},
                    {"shop_name": "Donatov.net", "price": 1250.0, "original_price": 1390.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/love-and-deepspace"},
                    {"shop_name": "PlayerOK", "price": 1290.0, "original_price": 1390.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                ],
            },
            {
                "package_type": "currency",
                "name": "1980 + 260 Кристаллов 💎",
                "amount": 1980,
                "bonus": 260,
                "icon": "fa-solid fa-gem",
                "sort_order": 4,
                "offers": [
                    {"shop_name": "BattlePass", "price": 2450.0, "original_price": 2790.0, "delivery_type": "uid", "delivery_time": "1-3 мин", "payment_methods": "СБП, Карты", "rating": 4.96, "reviews_count": 45000, "promo_code": "HLX", "promo_discount": "0% сбор", "url": "https://battlepass.ru/service/lovedspace"},
                    {"shop_name": "Donatov.net", "price": 2490.0, "original_price": 2790.0, "delivery_type": "uid", "delivery_time": "моментально", "payment_methods": "СБП, Карты", "rating": 4.92, "reviews_count": 13090, "promo_code": "GAMEDEALS", "promo_discount": "-5%", "url": "https://donatov.net/love-and-deepspace"},
                    {"shop_name": "PlayerOK", "price": 2570.0, "original_price": 2790.0, "delivery_type": "uid", "delivery_time": "2-5 мин", "payment_methods": "СБП, Карты", "rating": 4.9, "reviews_count": 28400, "promo_code": "GAMEDEALS", "promo_discount": "0% комиссия", "url": "https://playerok.com"},
                ],
            },
        ],
    },
]


def init_donate_database_logic():
    """Инициализирует или актуализирует базу данных доната для всех поддерживаемых игр."""
    db = SyncSessionLocal()
    try:
        for g_data in DONATE_CATALOG_DATA:
            existing_game = db.execute(
                select(DonateGame).where(DonateGame.slug == g_data["slug"])
            ).scalars().first()

            if not existing_game:
                game = DonateGame(
                    slug=g_data["slug"],
                    name=g_data["name"],
                    publisher=g_data["publisher"],
                    icon_url=g_data["icon_url"],
                    banner_url=g_data["banner_url"],
                    currency_name=g_data["currency_name"],
                    id_type=g_data["id_type"],
                    is_popular=g_data["is_popular"],
                    sort_order=g_data["sort_order"],
                )
                db.add(game)
                db.flush()
            else:
                game = existing_game
                game.name = g_data["name"]
                game.publisher = g_data["publisher"]
                game.currency_name = g_data["currency_name"]
                game.id_type = g_data["id_type"]
                game.sort_order = g_data["sort_order"]

            # Пакеты
            for p_data in g_data.get("packages", []):
                existing_pkg = db.execute(
                    select(DonatePackage)
                    .where(DonatePackage.game_id == game.id)
                    .where(DonatePackage.name == p_data["name"])
                ).scalars().first()

                if not existing_pkg:
                    pkg = DonatePackage(
                        game_id=game.id,
                        package_type=p_data["package_type"],
                        name=p_data["name"],
                        amount=p_data["amount"],
                        bonus=p_data["bonus"],
                        icon=p_data["icon"],
                        sort_order=p_data["sort_order"],
                    )
                    db.add(pkg)
                    db.flush()
                else:
                    pkg = existing_pkg
                    pkg.package_type = p_data["package_type"]
                    pkg.amount = p_data["amount"]
                    pkg.bonus = p_data["bonus"]
                    pkg.icon = p_data["icon"]
                    pkg.sort_order = p_data["sort_order"]

                # Предложения магазинов
                for o_data in p_data.get("offers", []):
                    existing_offer = db.execute(
                        select(DonateOffer)
                        .where(DonateOffer.package_id == pkg.id)
                        .where(DonateOffer.shop_name == o_data["shop_name"])
                    ).scalars().first()

                    if not existing_offer:
                        offer = DonateOffer(
                            package_id=pkg.id,
                            shop_name=o_data["shop_name"],
                            price=o_data["price"],
                            original_price=o_data.get("original_price"),
                            delivery_type=o_data.get("delivery_type", "uid"),
                            delivery_time=o_data.get("delivery_time", "1-3 мин"),
                            payment_methods=o_data.get("payment_methods", "СБП, Карты"),
                            rating=o_data.get("rating", 4.9),
                            reviews_count=o_data.get("reviews_count", 1000),
                            promo_code=o_data.get("promo_code"),
                            promo_discount=o_data.get("promo_discount"),
                            url=o_data["url"],
                            updated_at=datetime.utcnow(),
                        )
                        db.add(offer)
                    else:
                        offer = existing_offer
                        offer.price = o_data["price"]
                        offer.original_price = o_data.get("original_price")
                        offer.delivery_type = o_data.get("delivery_type", "uid")
                        offer.delivery_time = o_data.get("delivery_time", "1-3 мин")
                        offer.payment_methods = o_data.get("payment_methods", "СБП, Карты")
                        offer.rating = o_data.get("rating", 4.9)
                        offer.promo_code = o_data.get("promo_code")
                        offer.promo_discount = o_data.get("promo_discount")
                        offer.url = o_data["url"]
                        offer.updated_at = datetime.utcnow()

        db.commit()
        logger.info("Donate database successfully initialized/updated!")
        return True
    except Exception as e:
        db.rollback()
        logger.error("Error initializing donate database: %s", e)
        return False
    finally:
        db.close()


def get_all_donate_games():
    """Возвращает список всех игр со сводной статистикой (минимальная цена, кол-во пакетов)."""
    db = SyncSessionLocal()
    try:
        games = db.execute(
            select(DonateGame)
            .order_by(DonateGame.sort_order, DonateGame.name)
        ).scalars().all()

        result = []
        for g in games:
            min_price = None
            pkg_count = len(g.packages)
            for pkg in g.packages:
                for off in pkg.offers:
                    if min_price is None or off.price < min_price:
                        min_price = off.price

            result.append({
                "id": g.id,
                "slug": g.slug,
                "name": g.name,
                "publisher": g.publisher,
                "icon_url": g.icon_url,
                "banner_url": g.banner_url,
                "currency_name": g.currency_name,
                "id_type": g.id_type,
                "is_popular": g.is_popular,
                "package_count": pkg_count,
                "min_price": min_price or 0.0,
            })
        return result
    finally:
        db.close()


def get_donate_game_by_slug(slug: str):
    """Возвращает полную информацию об игре, её пакетах и офферах."""
    db = SyncSessionLocal()
    try:
        game = db.execute(
            select(DonateGame)
            .where(DonateGame.slug == slug)
            .options(
                selectinload(DonateGame.packages).selectinload(DonatePackage.offers)
            )
        ).scalars().first()

        if not game:
            return None

        packages_data = []
        for p in sorted(game.packages, key=lambda x: (x.sort_order, x.amount)):
            offers_data = []
            min_uid_price = None
            min_any_price = None

            for o in sorted(p.offers, key=lambda x: x.price):
                offers_data.append({
                    "id": o.id,
                    "shop_name": o.shop_name,
                    "price": o.price,
                    "original_price": o.original_price,
                    "delivery_type": o.delivery_type,  # uid, login, code
                    "delivery_time": o.delivery_time,
                    "payment_methods": o.payment_methods,
                    "rating": o.rating,
                    "reviews_count": o.reviews_count,
                    "promo_code": o.promo_code,
                    "promo_discount": o.promo_discount,
                    "url": o.url,
                    "updated_at": o.updated_at.isoformat() if o.updated_at else None,
                })
                if min_any_price is None or o.price < min_any_price:
                    min_any_price = o.price
                if o.delivery_type == "uid" and (min_uid_price is None or o.price < min_uid_price):
                    min_uid_price = o.price

            packages_data.append({
                "id": p.id,
                "package_type": p.package_type,
                "name": p.name,
                "amount": p.amount,
                "bonus": p.bonus,
                "icon": p.icon,
                "sort_order": p.sort_order,
                "min_price": min_any_price or 0.0,
                "min_uid_price": min_uid_price or min_any_price or 0.0,
                "offers_count": len(offers_data),
                "offers": offers_data,
            })

        return {
            "id": game.id,
            "slug": game.slug,
            "name": game.name,
            "publisher": game.publisher,
            "icon_url": game.icon_url,
            "banner_url": game.banner_url,
            "currency_name": game.currency_name,
            "id_type": game.id_type,
            "packages": packages_data,
        }
    finally:
        db.close()

