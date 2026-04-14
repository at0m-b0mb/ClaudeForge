"""
Performance benchmarking suite.
Measures CPU, memory, and overall compute capability.
"""

import time
import math
import os
import sys
import array
from dataclasses import dataclass


@dataclass
class BenchmarkResult:
    cpu_single_score: float   # Higher = faster single-core
    cpu_multi_score: float    # Higher = faster multi-core
    memory_bandwidth_gbps: float
    overall_score: float      # Normalized composite score (0-100)
    tier: str                 # "low", "mid", "high", "ultra"
    details: dict


def _benchmark_cpu_single(duration: float = 2.0) -> float:
    """
    Run a floating-point heavy workload for `duration` seconds.
    Returns operations-per-second (higher = faster).
    """
    ops = 0
    deadline = time.perf_counter() + duration
    x = 1.0
    while time.perf_counter() < deadline:
        # Mix of arithmetic + transcendental ops
        x = math.sqrt(abs(math.sin(x + 1.0) * math.cos(x) + 1e-9))
        x = math.log(x + 1.0) + math.exp(-x)
        ops += 1
    return ops / duration


def _benchmark_cpu_multi(duration: float = 2.0) -> float:
    """
    Run multi-threaded CPU benchmark using concurrent.futures.
    Returns aggregate operations-per-second.
    """
    try:
        from concurrent.futures import ThreadPoolExecutor
        import psutil
        n_threads = psutil.cpu_count(logical=True) or os.cpu_count() or 2
    except ImportError:
        n_threads = os.cpu_count() or 2

    results = []

    def worker():
        ops = 0
        deadline = time.perf_counter() + duration
        x = 1.0
        while time.perf_counter() < deadline:
            x = math.sqrt(abs(math.sin(x + 1.0) * math.cos(x) + 1e-9))
            x = math.log(x + 1.0) + math.exp(-x)
            ops += 1
        return ops

    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=n_threads) as pool:
            futures = [pool.submit(worker) for _ in range(n_threads)]
            for f in futures:
                results.append(f.result())
    except Exception:
        results.append(_benchmark_cpu_single(duration))

    total_ops = sum(results)
    return total_ops / duration


def _benchmark_memory(size_mb: int = 256) -> float:
    """
    Measure memory read bandwidth in GB/s.
    Allocates a buffer, then reads through it repeatedly.
    """
    element_count = (size_mb * 1024 * 1024) // 8  # 8 bytes per double
    buf = array.array("d", [1.0] * element_count)

    iterations = 3
    total_bytes = element_count * 8 * iterations

    start = time.perf_counter()
    total = 0.0
    for _ in range(iterations):
        for val in buf:
            total += val
    elapsed = time.perf_counter() - start

    # Prevent the optimizer from removing the loop
    _ = total

    gbps = (total_bytes / elapsed) / (1024 ** 3)
    return round(gbps, 3)


def _score_cpu(single: float, multi: float) -> float:
    """
    Normalize CPU ops/sec into a 0–100 score.
    Baselines are calibrated to a mid-range 2023 laptop.
    """
    # Rough calibration: ~5M single-core ops/s = score 50
    SINGLE_BASELINE = 5_000_000
    MULTI_BASELINE = 40_000_000
    single_score = min(100, (single / SINGLE_BASELINE) * 50)
    multi_score = min(100, (multi / MULTI_BASELINE) * 50)
    return round(single_score + multi_score, 1)


def _score_memory(bandwidth_gbps: float) -> float:
    """Normalize memory bandwidth to 0–100. Baseline: 30 GB/s = score 50."""
    BASELINE = 30.0
    return round(min(100, (bandwidth_gbps / BASELINE) * 50), 1)


def _compute_overall(cpu_score: float, mem_score: float, ram_gb: float, vram_mb: int) -> float:
    """Weighted composite score."""
    ram_score = min(100, (ram_gb / 64) * 100)  # 64 GB = 100
    gpu_score = min(100, (vram_mb / 24576) * 100)  # 24 GB VRAM = 100

    # Weights: CPU 40%, RAM 25%, Memory BW 15%, GPU 20%
    overall = (
        cpu_score * 0.40
        + ram_score * 0.25
        + mem_score * 0.15
        + gpu_score * 0.20
    )
    return round(overall, 1)


def _tier_from_score(score: float) -> str:
    if score >= 75:
        return "ultra"
    if score >= 50:
        return "high"
    if score >= 25:
        return "mid"
    return "low"


class Benchmarker:
    """
    Runs hardware benchmarks and returns a BenchmarkResult.

    Usage:
        b = Benchmarker(system_info)
        result = b.run(on_progress=callback)
    """

    def __init__(self, system_info=None):
        self.system_info = system_info

    def run(self, on_progress=None) -> BenchmarkResult:
        def progress(step: str):
            if on_progress:
                on_progress(step)

        progress("Running single-core CPU benchmark...")
        single = _benchmark_cpu_single(duration=2.0)

        progress("Running multi-core CPU benchmark...")
        multi = _benchmark_cpu_multi(duration=2.0)

        progress("Running memory bandwidth benchmark...")
        mem_bw = _benchmark_memory(size_mb=128)

        ram_gb = getattr(self.system_info, "ram_total_gb", 8.0) if self.system_info else 8.0
        gpus = getattr(self.system_info, "gpus", []) if self.system_info else []
        vram_mb = max((g.vram_mb for g in gpus), default=0)

        cpu_score = _score_cpu(single, multi)
        mem_score = _score_memory(mem_bw)
        overall = _compute_overall(cpu_score, mem_score, ram_gb, vram_mb)
        tier = _tier_from_score(overall)

        return BenchmarkResult(
            cpu_single_score=round(single, 0),
            cpu_multi_score=round(multi, 0),
            memory_bandwidth_gbps=mem_bw,
            overall_score=overall,
            tier=tier,
            details={
                "cpu_score": cpu_score,
                "mem_score": mem_score,
                "ram_gb": ram_gb,
                "vram_mb": vram_mb,
            },
        )
