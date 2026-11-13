import os
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"
import asyncio
import time
import httpx

async def bench(client: httpx.AsyncClient, name: str, url: str, total: int = 50, concurrency: int = 5):
    sem = asyncio.Semaphore(concurrency)
    latencies = []
    errors = 0

    async def worker():
        nonlocal errors
        async with sem:
            t0 = time.perf_counter()
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    latencies.append(time.perf_counter() - t0)
                else:
                    errors += 1
            except Exception:
                errors += 1

    t_start = time.perf_counter()
    await asyncio.gather(*(worker() for _ in range(total)))
    total_time = time.perf_counter() - t_start

    latencies.sort()
    rps = len(latencies) / total_time if total_time > 0 else 0
    p50 = latencies[int(len(latencies) * 0.50)] * 1000 if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] * 1000 if latencies else 0

    print(f"[{name}] {url}", flush=True)
    print(f"  • RPS: {rps:.1f} req/s | Total: {total} | Success: {len(latencies)} | Errors: {errors}", flush=True)
    print(f"  • Latency: median={p50:.1f}ms | p95={p95:.1f}ms | Duration: {total_time:.2f}s\n", flush=True)

async def main():
    print("=" * 60, flush=True)
    print("⚡ RUNNING SERVER BENCHMARK FOR LOOTOZAVR", flush=True)
    print("=" * 60 + "\n", flush=True)

    limits = httpx.Limits(max_keepalive_connections=10, max_connections=10)
    async with httpx.AsyncClient(limits=limits, timeout=5.0) as client:
        # 1. Homepage
        await bench(client, "Homepage (HTML SSR)", "http://localhost:8080/", total=50, concurrency=5)
        # 2. Topup Page
        await bench(client, "Top-up Page", "http://localhost:8080/topup", total=50, concurrency=5)
        # 3. Search Autocomplete API
        await bench(client, "Search API (Catalog Query)", "http://localhost:8080/api/catalog/search?query=Cyberpunk", total=100, concurrency=10)
        # 4. Discovery Popular API
        await bench(client, "Discovery Popular API", "http://localhost:8080/api/catalog/popular?mode=popular", total=60, concurrency=5)

if __name__ == "__main__":
    asyncio.run(main())
