from worker import parse_playerok_task

# Замените 1 на реальный game_id из БД
parse_playerok_task.delay(1, "Cyberpunk 2077", 99999, 0)
print("Задача отправлена")