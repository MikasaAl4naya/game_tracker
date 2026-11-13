"""Фикстуры pytest: пропускаем тесты если сайт недоступен из Docker."""
import pytest
import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}


def _site_available(url: str) -> bool:
    try:
        requests.get(url, headers=HEADERS, timeout=5)
        return True
    except Exception:
        return False


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: тесты с реальными HTTP-запросами")


plati_available = pytest.mark.skipif(
    not _site_available("https://plati.market/api/search.ashx?query=test&response=json"),
    reason="plati.market API недоступен из этой сети",
)

steambuy_available = pytest.mark.skipif(
    not _site_available("https://steambuy.com/sb/api/catalog/live?a=search&q=test")
    or not _site_available("https://steambuy.com"),
    reason="steambuy.com недоступен или SSL-ошибка из этой сети",
)
