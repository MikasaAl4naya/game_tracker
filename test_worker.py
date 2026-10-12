from worker import check_lot_validity

def test_perfect_steam_key_re4():
    # Обычный ключ (пропускаем)
    name = "Resident Evil 4 [STEAM Ключ]"
    props = "PC, Standard Edition, Цифровой ключ, Россия"
    assert check_lot_validity(name, props) is True

def test_perfect_steam_key_indie():
    # Инди-игра без указания издания (ОБЯЗАНА пройти, так как мы убрали костыль)
    name = "Terraria STEAM KEY RU"
    props = "PC, Цифровой ключ, Россия"
    assert check_lot_validity(name, props) is True

def test_reject_dlc_ticket():
    # Билетик прокачки (отсекаем по слову ticket/upgrade)
    name = "Resident Evil 4 Weapon Exclusive Upgrade Ticket x1"
    props = "PC, Цифровой ключ, Россия"
    assert check_lot_validity(name, props) is False

def test_reject_nvidia_hardware_promo():
    # Железячный ключ
    name = "Ключ на игру ⚠️ Для ГПУ ≥ RTX 5070"
    props = "PC, Цифровой ключ, Global"
    assert check_lot_validity(name, props) is False

def test_reject_console_account():
    # Консольный аккаунт
    name = "Игра П1 НАВСЕГДА"
    props = "PS5, Цифровой ключ"
    assert check_lot_validity(name, props) is False