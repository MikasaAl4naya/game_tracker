#!/usr/bin/env python3
"""
Скрипт для замера средней скорости скачивания файла по URL.

Выполняет последовательные синхронные HTTP GET-запросы с замером времени
скачивания полного тела ответа и расчетом скорости передачи данных в Мбит/с.
Использует исключительно стандартную библиотеку Python (3.10+).
"""

from __future__ import annotations

import argparse
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

# Константы конфигурации по умолчанию
DEFAULT_NUM_REQUESTS: int = 10
DEFAULT_TIMEOUT_SEC: float = 30.0
DEFAULT_CHUNK_SIZE: int = 64 * 1024  # 64 КиБ для потокового чтения без перегрузки RAM
USER_AGENT: str = "Mozilla/5.0"

# Метрические константы
BITS_IN_BYTE: int = 8
BITS_IN_MEGABIT: float = 1_000_000.0  # Сетевой стандарт SI: 1 Мбит = 1 000 000 бит
BYTES_IN_MB: float = 1024.0 * 1024.0   # Двоичный мегабайт (MiB) для объема файлов


@dataclass(frozen=True, slots=True)
class IterationResult:
    """Результат выполнения одного сетевого запроса."""

    index: int
    success: bool
    bytes_downloaded: int = 0
    duration: float = 0.0
    status_code: int | None = None
    error_message: str | None = None

    @property
    def megabytes(self) -> float:
        """Объем данных в мегабайтах (MiB)."""
        return self.bytes_downloaded / BYTES_IN_MB

    @property
    def speed_mbps(self) -> float:
        """
        Скорость передачи данных в Мбит/с (Mbps).
        Формула: (Байты / Секунды) * 8 / 1_000_000.
        """
        if self.duration <= 0 or self.bytes_downloaded <= 0:
            return 0.0
        return (self.bytes_downloaded / self.duration) * BITS_IN_BYTE / BITS_IN_MEGABIT


@dataclass(frozen=True, slots=True)
class SpeedTestSummary:
    """Итоговая статистика по всей серии запросов."""

    total_requests: int
    successful_requests: int
    failed_requests: int
    total_bytes: int
    total_duration_sec: float
    avg_duration_sec: float
    avg_speed_mbps: float

    @property
    def total_megabytes(self) -> float:
        """Общий объем скачанных данных в МБ."""
        return self.total_bytes / BYTES_IN_MB


def validate_url(raw_url: str) -> str:
    """
    Валидирует переданный URL-адрес.
    Проверяет наличие схемы (http/https) и сетевого адреса (netloc).
    """
    url = raw_url.strip()
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise argparse.ArgumentTypeError(
            f"Некорректный URL: '{raw_url}'. Адрес должен начинаться с 'http://' или 'https://'."
        )
    return url


def positive_int(value: str) -> int:
    """Валидатор положительного целого числа для argparse."""
    try:
        val = int(value)
        if val <= 0:
            raise ValueError
        return val
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Значение должно быть положительным целым числом (> 0), получено: '{value}'"
        )


def positive_float(value: str) -> float:
    """Валидатор положительного вещественного числа для argparse."""
    try:
        val = float(value)
        if val <= 0:
            raise ValueError
        return val
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Значение должно быть положительным числом (> 0), получено: '{value}'"
        )


def download_iteration(
    url: str,
    index: int,
    timeout: float = DEFAULT_TIMEOUT_SEC,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> IterationResult:
    """
    Выполняет один синхронный GET-запрос к указанному URL и полностью скачивает тело ответа.

    Тело ответа считывается потоково порциями (chunk_size), что гарантирует
    реальную загрузку данных по сети без накопления тяжелых объектов в оперативной памяти (O(1) RAM).
    Время замеряется строго через time.perf_counter().
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Connection": "close",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")

    start_time = time.perf_counter()
    bytes_count = 0
    status_code: int | None = None

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = getattr(response, "status", 200)

            # Потоковое чтение полного тела ответа до EOF (empty bytes)
            while chunk := response.read(chunk_size):
                bytes_count += len(chunk)

        elapsed = time.perf_counter() - start_time
        return IterationResult(
            index=index,
            success=True,
            bytes_downloaded=bytes_count,
            duration=elapsed,
            status_code=status_code,
        )

    except urllib.error.HTTPError as exc:
        elapsed = time.perf_counter() - start_time
        return IterationResult(
            index=index,
            success=False,
            duration=elapsed,
            status_code=exc.code,
            error_message=f"HTTP {exc.code}: {exc.reason}",
        )
    except urllib.error.URLError as exc:
        elapsed = time.perf_counter() - start_time
        # exc.reason может быть исключением (например socket.gaierror) или строкой
        reason = getattr(exc.reason, "strerror", str(exc.reason))
        return IterationResult(
            index=index,
            success=False,
            duration=elapsed,
            error_message=f"Сетевая ошибка: {reason}",
        )
    except (TimeoutError, socket.timeout):
        elapsed = time.perf_counter() - start_time
        return IterationResult(
            index=index,
            success=False,
            duration=elapsed,
            error_message=f"Превышен таймаут ответа ({timeout:.1f} с)",
        )
    except Exception as exc:  # Защита от непредвиденных сбоев соединения
        elapsed = time.perf_counter() - start_time
        return IterationResult(
            index=index,
            success=False,
            duration=elapsed,
            error_message=f"Непредвиденная ошибка: {exc}",
        )


def calculate_summary(results: list[IterationResult]) -> SpeedTestSummary:
    """
    Вычисляет сводную статистику по серии запросов.

    Для расчета средней скорости используется формула ТЗ:
      (Общий объем в байтах / Общее время в секундах) * 8 / 1_000_000
    Предусмотрена строгая защита от деления на ноль.
    """
    total_requests = len(results)
    successful = [r for r in results if r.success]
    failed_requests = total_requests - len(successful)

    total_bytes = sum(r.bytes_downloaded for r in successful)
    total_duration_sec = sum(r.duration for r in successful)

    avg_duration_sec = (
        (total_duration_sec / len(successful)) if len(successful) > 0 else 0.0
    )

    # Защита от деления на ноль
    if total_duration_sec > 0 and total_bytes > 0:
        avg_speed_mbps = (
            (total_bytes / total_duration_sec) * BITS_IN_BYTE / BITS_IN_MEGABIT
        )
    else:
        avg_speed_mbps = 0.0

    return SpeedTestSummary(
        total_requests=total_requests,
        successful_requests=len(successful),
        failed_requests=failed_requests,
        total_bytes=total_bytes,
        total_duration_sec=total_duration_sec,
        avg_duration_sec=avg_duration_sec,
        avg_speed_mbps=avg_speed_mbps,
    )


def print_iteration_progress(result: IterationResult, total: int) -> None:
    """Выводит информацию о текущей завершенной итерации."""
    width = len(str(total))
    prefix = f"[{result.index:>{width}}/{total}]"

    if result.success:
        print(
            f"{prefix} Успешно  | "
            f"Время: {result.duration:6.2f} с | "
            f"Объём: {result.megabytes:7.2f} МБ | "
            f"Скорость: {result.speed_mbps:8.2f} Мбит/с"
        )
    else:
        err = result.error_message or "Неизвестная ошибка"
        print(f"{prefix} ОШИБКА   | Время: {result.duration:6.2f} с | {err}")


def print_summary(summary: SpeedTestSummary) -> None:
    """Выводит итоговую статистику тестирования."""
    sep = "=" * 64
    print("\n" + sep)
    print("ИТОГОВАЯ СТАТИСТИКА ЗАМЕРА СКОРОСТИ".center(64))
    print(sep)
    print(
        f"Запросов выполнено:         {summary.successful_requests} из {summary.total_requests} "
        f"успешно"
        + (f" ({summary.failed_requests} с ошибками)" if summary.failed_requests else "")
    )
    print(
        f"Общий объём данных:         {summary.total_megabytes:.2f} МБ "
        f"({summary.total_bytes:,} байт)"
    )
    print(f"Суммарное время скачивания: {summary.total_duration_sec:.2f} с")
    print(f"Среднее время одного запроса:{summary.avg_duration_sec:7.2f} с")
    print(f"Средняя скорость:           {summary.avg_speed_mbps:.2f} Мбит/с (Mbps)")
    print(sep)


def run_speedtest(
    url: str,
    num_requests: int = DEFAULT_NUM_REQUESTS,
    timeout: float = DEFAULT_TIMEOUT_SEC,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> SpeedTestSummary:
    """
    Основной цикл синхронного тестирования скорости скачивания.
    Делает num_requests последовательных запросов, дожидаясь полного ответа на каждый.
    """
    print(f"Тестируемый URL: {url}")
    print(f"Количество последовательных запросов: {num_requests}")
    print(f"Таймаут одного запроса: {timeout:.1f} с")
    print("-" * 64)

    results: list[IterationResult] = []

    for i in range(1, num_requests + 1):
        result = download_iteration(
            url=url,
            index=i,
            timeout=timeout,
            chunk_size=chunk_size,
        )
        results.append(result)
        print_iteration_progress(result, num_requests)

    summary = calculate_summary(results)
    print_summary(summary)
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    """Создает парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="speedtest.py",
        description="Консольный инструмент для замера скорости скачивания файла по URL (Python 3.10+).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "url",
        type=validate_url,
        help="Прямой URL-адрес файла для скачивания (http:// или https://)",
    )
    parser.add_argument(
        "-n",
        "--num-requests",
        type=positive_int,
        default=DEFAULT_NUM_REQUESTS,
        help="Количество последовательных запросов",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=positive_float,
        default=DEFAULT_TIMEOUT_SEC,
        help="Таймаут на один запрос в секундах",
    )
    parser.add_argument(
        "-c",
        "--chunk-size",
        type=positive_int,
        default=DEFAULT_CHUNK_SIZE,
        help="Размер буфера потокового чтения в байтах",
    )
    return parser


def main() -> int:
    """Точка входа в программу."""
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        summary = run_speedtest(
            url=args.url,
            num_requests=args.num_requests,
            timeout=args.timeout,
            chunk_size=args.chunk_size,
        )
        # Если ни один запрос не завершился успехом, завершаем с кодом 1
        return 0 if summary.successful_requests > 0 else 1

    except KeyboardInterrupt:
        print("\n\n[!] Замер прерван пользователем (Ctrl+C).", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"\n[Критическая ошибка] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
