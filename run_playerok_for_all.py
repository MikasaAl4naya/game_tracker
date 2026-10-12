from worker import get_all_catalog_games, parse_playerok_task

def main():
    print("Получаем список всех игр из каталога...")
    games = get_all_catalog_games()
    print(f"Найдено {len(games)} игр. Отправляем задачи parse_playerok_task в очередь...")

    for game in games:
        # target_price = 99999 (игнорировать порог), chat_id = 0
        parse_playerok_task.delay(game.id, game.name, 99999, 0)

    print("Все задачи успешно поставлены. Проверьте логи воркера для отслеживания выполнения.")

if __name__ == "__main__":
    main()