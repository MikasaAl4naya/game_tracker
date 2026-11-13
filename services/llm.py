import hashlib
import json
import logging
import re
import requests

from services.config import OLLAMA_URL, redis_client
from services.filters import check_lot_validity, detect_platform, detect_region

logger = logging.getLogger(__name__)

_OLLAMA_AVAILABLE: bool | None = None

_LLM_SYSTEM_PROMPT = """Ты — классификатор товаров игрового маркетплейса.
На вход ты получишь JSON-массив объектов. Твоя задача проанализировать КАЖДЫЙ лот и вернуть JSON-МАССИВ ответов.

Правила валидности (is_valid):
- true: цифровой ключ (key), гифт (gift), код.
- false: аккаунт, аренда, услуги, буст, оффлайн, смена данных, DLC, скины.

Формат ответа — СТРОГО JSON-массив:
[
  {"id": 0, "is_valid": true, "platform": "Steam", "region": "RU"},
  {"id": 1, "is_valid": false, "platform": "Unknown", "region": "Unknown"}
]
"""


def _check_ollama() -> bool:
    """Проверяет доступность Ollama и кэширует результат на 60 секунд в Redis."""
    global _OLLAMA_AVAILABLE
    if _OLLAMA_AVAILABLE is not None:
        return _OLLAMA_AVAILABLE

    cache_key = "ollama:available"
    try:
        cached = redis_client.get(cache_key)
        if cached is not None:
            _OLLAMA_AVAILABLE = cached == "1"
            return _OLLAMA_AVAILABLE
    except Exception:
        pass

    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        _OLLAMA_AVAILABLE = (resp.status_code == 200)
    except Exception:
        _OLLAMA_AVAILABLE = False

    try:
        redis_client.setex(cache_key, 60, "1" if _OLLAMA_AVAILABLE else "0")
    except Exception:
        pass

    return _OLLAMA_AVAILABLE


def _llm_fallback(item: dict) -> dict:
    """Применяет regex-фильтр как замену LLM для одного лота."""
    item["is_valid"] = check_lot_validity(item["name"], item.get("props", ""))
    item["platform"] = detect_platform(item["name"], drm=item.get("props", ""))
    item["region"] = detect_region(item["name"] + " " + item.get("props", ""))
    return item


def process_candidates_batch(candidates: list[dict]) -> list[dict]:
    """Проверяет кэш Redis; некэшированные лоты отправляет пачками по 10 в LLM."""
    results: list[dict] = []
    to_check_llm: list[dict] = []

    redis_available = True
    for cand in candidates:
        cache_key = "llm_cache:" + hashlib.md5(
            (cand["name"] + " " + cand.get("props", "")).encode()
        ).hexdigest()
        if redis_available:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    cand["is_valid"] = data["is_valid"]
                    cand["platform"] = data["platform"]
                    cand["region"] = data["region"]
                    results.append(cand)
                    continue
            except Exception:
                redis_available = False
        cand["_cache_key"] = cache_key
        to_check_llm.append(cand)

    batch_size = 10
    ollama_up = _check_ollama()

    for i in range(0, len(to_check_llm), batch_size):
        batch = to_check_llm[i : i + batch_size]

        if not ollama_up:
            for b in batch:
                results.append(_llm_fallback(b))
            continue

        prompt_data = [{"id": j, "name": b["name"], "props": b.get("props", "")} for j, b in enumerate(batch)]

        payload = {
            "model": "llama3.2:3b",
            "prompt": f"{_LLM_SYSTEM_PROMPT}\n\nВход:\n{json.dumps(prompt_data, ensure_ascii=False)}",
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.0},
        }

        try:
            resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=10)
            resp.raise_for_status()
            llm_results = json.loads(
                re.sub(r"```json|```", "", resp.json().get("response", "")).strip()
            )

            processed_ids: set[int] = set()
            for res in llm_results:
                idx = res.get("id")
                if idx is None or not (0 <= idx < len(batch)):
                    continue
                b = batch[idx]
                b["is_valid"] = res.get("is_valid", False)
                plat = res.get("platform", "Unknown")
                b["platform"] = plat if plat and plat != "Unknown" else detect_platform(b["name"], drm=b.get("props", ""))
                b["region"] = res.get("region", "Unknown")
                try:
                    redis_client.setex(
                        b["_cache_key"],
                        2_592_000,  # 30 дней
                        json.dumps({"is_valid": b["is_valid"], "platform": b["platform"], "region": b["region"]}),
                    )
                except Exception:
                    pass
                results.append(b)
                processed_ids.add(idx)
                icon = "✅" if b["is_valid"] else "❌"
                logger.debug("%s ИИ [%s|%s]: %s", icon, b["region"], b["platform"], b["name"])

            for j, b in enumerate(batch):
                if j not in processed_ids:
                    results.append(_llm_fallback(b))

        except Exception as e:
            logger.warning("Ошибка LLM (батч %d): %s — переключаюсь на regex", i // batch_size + 1, e)
            for b in batch:
                results.append(_llm_fallback(b))

    return results
