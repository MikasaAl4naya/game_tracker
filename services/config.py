import os
from dotenv import load_dotenv
import redis

load_dotenv()

NO_PRICE_LIMIT: float = 99_999.0

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

redis_client = redis.Redis.from_url(
    f"{REDIS_URL}/1",
    decode_responses=True,
    socket_connect_timeout=0.3,
    socket_timeout=0.3,
)
