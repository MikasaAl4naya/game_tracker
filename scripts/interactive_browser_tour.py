import os
import sys
import time
from playwright.sync_api import sync_playwright

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE_URL = "http://localhost:8080"


def run_interactive_tour():
    print("\n========================================================")
    print(" ЗАПУСК ВИДИМОГО БРАУЗЕРА (HEADED MODE) ДЛЯ ПРОКЛИКИВАНИЯ")
    print("========================================================")

    with sync_playwright() as p:
        # Запускаем браузер в видимом режиме (headless=False) с плавной задержкой (slow_mo)
        browser = p.chromium.launch(
            executable_path=EDGE_PATH,
            headless=False,
            slow_mo=600,
            args=["--start-maximized", "--disable-gpu"]
        )
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        # ----------------------------------------------------
        # Сценарий 1: Главная страница и вкладка «Скидки»
        # ----------------------------------------------------
        print("\n[Шаг 1] Открываем главную страницу...")
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        time.sleep(1.5)

        print("[Шаг 1.1] Скроллим к каталогу и кликаем на вкладку «Скидки»...")
        page.evaluate("window.scrollTo({ top: 400, behavior: 'smooth' })")
        time.sleep(1)

        deals_btn = page.locator(".discovery-tab[data-tab='deals']")
        deals_btn.click()
        time.sleep(2)

        # ----------------------------------------------------
        # Сценарий 2: Единый живой поиск — Донат в Genshin Impact
        # ----------------------------------------------------
        print("\n[Шаг 2] Скроллим наверх к поиску...")
        page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' })")
        time.sleep(1)

        search_input = page.locator("#searchInput")
        search_input.click()
        search_input.type("Genshin", delay=120)
        time.sleep(1.5)

        print("[Шаг 2.1] Кликаем по найденной плашке '💎 Донат Genshin Impact' в подсказках...")
        donate_hint = page.locator("#searchSuggestions div:has-text('Донат')").first
        donate_hint.click()
        time.sleep(2)

        # ----------------------------------------------------
        # Сценарий 3: Раздел доната — переключение игр и пакетов
        # ----------------------------------------------------
        print("\n[Шаг 3] Мы в разделе Доната! Переключаем игры...")
        brawl_chip = page.locator("#donateGamesChips .donate-game-chip:has-text('Brawl Stars')")
        brawl_chip.click()
        time.sleep(2)

        roblox_chip = page.locator("#donateGamesChips .donate-game-chip:has-text('Roblox')")
        roblox_chip.click()
        time.sleep(2)

        genshin_chip = page.locator("#donateGamesChips .donate-game-chip:has-text('Genshin Impact')")
        genshin_chip.click()
        time.sleep(2)

        print("[Шаг 3.1] Кликаем по тумблеру безопасности 'Только по UID'...")
        uid_toggle = page.locator("#donateUidToggleBtn")
        uid_toggle.click() # Показываем все способы (включая вход)
        time.sleep(2)
        uid_toggle.click() # Возвращаем безопасный режим только по UID
        time.sleep(1.5)

        print("[Шаг 3.2] Копируем промокод GAMEDEALS...")
        copy_promo_btn = page.locator("#donateGameBanner button:has-text('Копировать')")
        copy_promo_btn.click()
        time.sleep(2)

        print("[Шаг 3.3] Раскрываем аккордеон FAQ по безопасности UID...")
        page.evaluate("window.scrollTo({ top: 900, behavior: 'smooth' })")
        time.sleep(1)
        faq_btn = page.locator("#donateState button:has-text('Безопасно ли пополнять аккаунт по UID?')")
        faq_btn.click()
        time.sleep(2)
        faq_btn.click()
        time.sleep(1)

        # ----------------------------------------------------
        # Сценарий 4: Пополнение Steam (/topup)
        # ----------------------------------------------------
        print("\n[Шаг 4] Переходим в раздел «Пополнение Steam» через шапку...")
        page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' })")
        time.sleep(0.5)

        topup_nav = page.locator("header nav a[href='/topup']")
        topup_nav.click()
        time.sleep(2)

        print("[Шаг 4.1] Вводим сумму 2500 руб в калькулятор пополнения...")
        topup_input = page.locator("#topupAmountInput")
        topup_input.fill("")
        topup_input.type("2500", delay=100)
        time.sleep(2)

        # Переключаем способ на СБП
        sbp_btn = page.locator(".topup-method-btn[data-method='sbp']")
        if sbp_btn.count() > 0:
            sbp_btn.first.click()
            time.sleep(1.5)

        # ----------------------------------------------------
        # Сценарий 5: Поиск игры Steam (Cyberpunk 2077)
        # ----------------------------------------------------
        print("\n[Шаг 5] Ищем игру Steam 'Cyberpunk 2077' через шапку...")
        search_input.click()
        search_input.fill("")
        search_input.type("Cyberpunk 2077", delay=80)
        time.sleep(1.5)

        cyber_hint = page.locator("#searchSuggestions div:has-text('Cyberpunk 2077')").first
        cyber_hint.click()
        time.sleep(2.5)

        print("[Шаг 5.1] На странице игры: переключаем фильтры формата и региона...")
        page.evaluate("window.scrollTo({ top: 350, behavior: 'smooth' })")
        time.sleep(1)

        # Фильтр ключи
        key_filter = page.locator(".format-pill:has-text('Ключи')")
        if key_filter.count() > 0:
            key_filter.first.click()
            time.sleep(1.5)

        # Фильтр гифты
        gift_filter = page.locator(".format-pill:has-text('Гифты')")
        if gift_filter.count() > 0:
            gift_filter.first.click()
            time.sleep(1.5)

        all_filter = page.locator(".format-pill:has-text('Все')")
        if all_filter.count() > 0:
            all_filter.first.click()
            time.sleep(1.5)

        print("\n[Финал] Все сценарии успешно прокликаны в реальном браузере!")
        time.sleep(3)
        browser.close()


if __name__ == "__main__":
    run_interactive_tour()
