import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

_session: requests.Session | None = None


def get_http_session() -> requests.Session:
    """Возвращает переиспользуемую сессию с connection pool и автоматическими ретраями."""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.trust_env = False
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=retries)
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
        _session.headers.update(DEFAULT_HEADERS)
    return _session
