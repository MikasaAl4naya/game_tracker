import redis

# Подключаемся именно к той базе, которую прописали в воркере (база №1)
redis_client = redis.Redis.from_url("redis://localhost:6379/1")

try:
    count = redis_client.dbsize()
    print(f"В базе Redis сейчас ключей: {count}")

    # Полная очистка
    redis_client.flushdb()
    print("🧹 Redis успешно очищен!")
except Exception as e:
    print(f"Ошибка подключения к Redis: {e}")