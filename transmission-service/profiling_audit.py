"""
Performance Profiling Script for Transmission Service
=====================================================
Uses cProfile, tracemalloc, and custom analysis to identify bottlenecks.

Usage:
    python profiling_audit.py

This script performs static analysis + simulated profiling of the core
transmission service components without requiring a running database.
"""

import cProfile
import pstats
import tracemalloc
import sys
import os
import io
import time
import json
import csv
import random
import asyncio
from pstats import SortKey
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

# ============================================================
# 1. CPU Profiling — Simulate hot-path functions
# ============================================================

def simulate_build_payload(num_iterations: int = 10000):
    """Profile _build_payload — called once per message."""
    results = []
    for i in range(num_iterations):
        payload: Dict[str, Any] = {}
        payload["device_id"] = f"DEV{i:04d}"
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        payload["data"] = {
            "temperature": round(random.uniform(20.0, 35.0), 2),
            "humidity": round(random.uniform(30.0, 80.0), 2),
            "pressure": round(random.uniform(990.0, 1030.0), 2),
        }
        results.append(payload)
    return results


def simulate_json_serialization(payloads: List[Dict]):
    """Profile json.dumps — called for every message + every log entry."""
    sizes = []
    for p in payloads:
        serialized = json.dumps(p)
        sizes.append(len(serialized))
    return sizes


def simulate_csv_read(num_rows: int = 50000):
    """Profile _read_dataset_file CSV path — called on device monitor refresh."""
    # Create in-memory CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["temperature", "humidity", "pressure", "timestamp"])
    writer.writeheader()
    for i in range(num_rows):
        writer.writerow({
            "temperature": round(random.uniform(20.0, 35.0), 2),
            "humidity": round(random.uniform(30.0, 80.0), 2),
            "pressure": round(random.uniform(990.0, 1030.0), 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # Read it back (simulating _read_dataset_file)
    output.seek(0)
    reader = csv.DictReader(output)
    rows = []
    for row in reader:
        rows.append(dict(row))  # dict(row) creates a new dict each time
    return rows


def simulate_transmission_log_creation(num_logs: int = 5000):
    """Profile TransmissionLog object creation + json.dumps for payload_size."""
    logs = []
    for i in range(num_logs):
        payload = {
            "device_id": f"DEV{i:04d}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"temp": 25.0 + random.random()},
        }
        log_meta = {
            "row_index": i,
            "batch_size": 1,
            "pooled": True,
        }
        # This mirrors the hot path in _transmit_for_device
        payload_size = len(json.dumps(payload))
        logs.append({
            "device_id": f"uuid-{i}",
            "payload_size": payload_size,
            "message_content": payload,
            "log_metadata": log_meta,
            "status": "success",
            "latency_ms": random.uniform(5, 50),
        })
    return logs


def simulate_stats_computation(active_devices: int = 500):
    """Profile stats computation done every transmission tick."""
    # Simulates set comprehension for active_connections count
    devices = {
        f"dev-{i}": {"connection_id": f"conn-{i % 50}"}
        for i in range(active_devices)
    }
    # This is called every _update_active_devices cycle
    active_connections = len(set(d["connection_id"] for d in devices.values()))
    
    # Simulates bytes_transmitted sum
    logs = [{"payload_size": random.randint(100, 2000)} for _ in range(active_devices)]
    bytes_total = sum(l["payload_size"] for l in logs)
    
    return active_connections, bytes_total


def run_cpu_profiling():
    """Run cProfile on simulated hot paths."""
    print("=" * 70)
    print("CPU PROFILING — cProfile Analysis")
    print("=" * 70)

    profiler = cProfile.Profile()
    profiler.enable()

    # Simulate hot paths
    payloads = simulate_build_payload(10000)
    sizes = simulate_json_serialization(payloads)
    rows = simulate_csv_read(50000)
    logs = simulate_transmission_log_creation(5000)
    stats = simulate_stats_computation(500)

    profiler.disable()

    # Print top functions by cumulative time
    stream = io.StringIO()
    stats_obj = pstats.Stats(profiler, stream=stream)
    stats_obj.sort_stats(SortKey.CUMULATIVE)
    stats_obj.print_stats(30)
    print(stream.getvalue())

    # Print top by total time (self time)
    stream2 = io.StringIO()
    stats_obj2 = pstats.Stats(profiler, stream=stream2)
    stats_obj2.sort_stats(SortKey.TIME)
    stats_obj2.print_stats(20)
    print("\n--- Top functions by SELF time ---")
    print(stream2.getvalue())

    # Save profile for external analysis
    stats_obj.dump_stats("transmission_profile.prof")
    print("Profile saved to transmission_profile.prof")
    print(f"  (Use: python -m pstats transmission_profile.prof)")

    return profiler


# ============================================================
# 2. Memory Profiling — tracemalloc
# ============================================================

def run_memory_profiling():
    """Track memory allocations for key operations."""
    print("\n" + "=" * 70)
    print("MEMORY PROFILING — tracemalloc Analysis")
    print("=" * 70)

    tracemalloc.start()

    # Snapshot before
    snapshot1 = tracemalloc.take_snapshot()

    # Simulate dataset loading (main memory consumer)
    all_rows = []
    for _ in range(10):  # 10 devices, each with 5000 rows
        rows = simulate_csv_read(5000)
        all_rows.append(rows)

    snapshot2 = tracemalloc.take_snapshot()

    # Compare
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    print("\nTop 15 memory allocations (dataset loading):")
    for stat in top_stats[:15]:
        print(f"  {stat}")

    # Current memory usage
    current, peak = tracemalloc.get_traced_memory()
    print(f"\nCurrent memory: {current / 1024 / 1024:.2f} MB")
    print(f"Peak memory:    {peak / 1024 / 1024:.2f} MB")

    # Simulate payload accumulation (transmission logs)
    snapshot3 = tracemalloc.take_snapshot()
    
    accumulated_logs = []
    for _ in range(20):  # 20 transmission cycles
        logs = simulate_transmission_log_creation(500)
        accumulated_logs.extend(logs)

    snapshot4 = tracemalloc.take_snapshot()
    
    top_stats2 = snapshot4.compare_to(snapshot3, 'lineno')
    print("\nTop 10 memory allocations (log accumulation):")
    for stat in top_stats2[:10]:
        print(f"  {stat}")

    current2, peak2 = tracemalloc.get_traced_memory()
    print(f"\nCurrent memory after logs: {current2 / 1024 / 1024:.2f} MB")
    print(f"Peak memory after logs:    {peak2 / 1024 / 1024:.2f} MB")

    tracemalloc.stop()


# ============================================================
# 3. I/O Pattern Analysis
# ============================================================

def analyze_io_patterns():
    """Analyze I/O patterns from code structure."""
    print("\n" + "=" * 70)
    print("I/O PATTERN ANALYSIS")
    print("=" * 70)

    findings = []

    # Finding 1: Dataset reload every 5 seconds
    findings.append({
        "component": "_device_monitor / _update_active_devices",
        "interval": "Every 5 seconds",
        "issue": "Reloads ALL dataset CSV files for ALL active devices from disk + DB",
        "impact": "HIGH — For 50 devices with 10K-row datasets, reads ~500K rows every 5s",
        "db_queries": "1 (device list) + N (dataset links) + N (dataset metadata) per device",
    })

    # Finding 2: Connection fetch per transmission
    findings.append({
        "component": "_transmit_for_device",
        "interval": "Every device transmission cycle",
        "issue": "Opens new AsyncSession and queries Connection table for EVERY transmission",
        "impact": "MEDIUM — DB round-trip per message even though connection config rarely changes",
        "db_queries": "1 SELECT per transmission cycle per device",
    })

    # Finding 3: Device status updates
    findings.append({
        "component": "_transmit_for_device / _set_device_status",
        "interval": "Every transmission cycle",
        "issue": "UPDATE + COMMIT for device row_index after every batch",
        "impact": "MEDIUM — Separate session open/commit for each device update",
        "db_queries": "1 UPDATE + 1 COMMIT per device per cycle",
    })

    # Finding 4: TransmissionLog INSERT per message
    findings.append({
        "component": "_transmit_for_device",
        "interval": "Every message",
        "issue": "Creates TransmissionLog ORM object + json.dumps(payload) for payload_size",
        "impact": "MEDIUM — ORM overhead + double serialization (publish + log)",
        "db_queries": "Batch INSERT via session.add_all(), but still ORM overhead",
    })

    # Finding 5: MQTT non-pooled creates new connection per publish
    findings.append({
        "component": "MQTTHandler.publish (non-pooled fallback)",
        "interval": "On pool failure",
        "issue": "Creates new MQTT client, connects, publishes, disconnects for EACH message",
        "impact": "HIGH — TCP handshake + MQTT CONNECT/DISCONNECT per message",
        "db_queries": "N/A (network I/O)",
    })

    # Finding 6: Kafka future.get() blocking
    findings.append({
        "component": "KafkaHandler.publish / publish_pooled",
        "interval": "Every Kafka message",
        "issue": "Calls future.get(timeout) in executor — blocks thread pool thread",
        "impact": "MEDIUM — Synchronous wait in thread pool; no batching/linger_ms configured",
        "db_queries": "N/A (network I/O)",
    })

    for i, f in enumerate(findings, 1):
        print(f"\n  [{i}] {f['component']}")
        print(f"      Interval: {f['interval']}")
        print(f"      Issue:    {f['issue']}")
        print(f"      Impact:   {f['impact']}")
        print(f"      DB Ops:   {f['db_queries']}")


# ============================================================
# 4. Timing Benchmarks
# ============================================================

def run_timing_benchmarks():
    """Benchmark individual operations."""
    print("\n" + "=" * 70)
    print("TIMING BENCHMARKS")
    print("=" * 70)

    benchmarks = {}

    # Benchmark: json.dumps
    payload = {
        "device_id": "DEV0001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {"temperature": 25.5, "humidity": 60.0, "pressure": 1013.25},
    }
    start = time.perf_counter()
    for _ in range(100000):
        json.dumps(payload)
    elapsed = time.perf_counter() - start
    benchmarks["json.dumps (100K calls)"] = elapsed

    # Benchmark: datetime.now().isoformat()
    start = time.perf_counter()
    for _ in range(100000):
        datetime.now(timezone.utc).isoformat()
    elapsed = time.perf_counter() - start
    benchmarks["datetime.now().isoformat() (100K)"] = elapsed

    # Benchmark: CSV read 10K rows
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["a", "b", "c"])
    writer.writeheader()
    for i in range(10000):
        writer.writerow({"a": i, "b": i * 2, "c": i * 3})
    csv_data = output.getvalue()

    start = time.perf_counter()
    for _ in range(10):
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = [dict(row) for row in reader]
    elapsed = time.perf_counter() - start
    benchmarks["CSV DictReader 10K rows (10 reads)"] = elapsed

    # Benchmark: len(json.dumps(payload)) — double serialization
    start = time.perf_counter()
    for _ in range(100000):
        len(json.dumps(payload))
    elapsed = time.perf_counter() - start
    benchmarks["len(json.dumps()) for payload_size (100K)"] = elapsed

    # Benchmark: set comprehension for active connections
    devices = {f"dev-{i}": f"conn-{i % 50}" for i in range(1000)}
    start = time.perf_counter()
    for _ in range(10000):
        len(set(devices.values()))
    elapsed = time.perf_counter() - start
    benchmarks["set() for active_connections (10K, 1000 devices)"] = elapsed

    # Benchmark: random.randint for jitter
    start = time.perf_counter()
    for _ in range(100000):
        random.randint(0, 500) / 1000
    elapsed = time.perf_counter() - start
    benchmarks["random.randint jitter (100K)"] = elapsed

    for name, elapsed in benchmarks.items():
        print(f"  {name}: {elapsed:.4f}s")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    print("Transmission Service — Performance Audit Profiling")
    print("=" * 70)
    print(f"Python {sys.version}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    run_cpu_profiling()
    run_memory_profiling()
    analyze_io_patterns()
    run_timing_benchmarks()

    print("\n" + "=" * 70)
    print("PROFILING COMPLETE")
    print("=" * 70)
    print("See transmission_profile.prof for detailed cProfile data.")
    print("Run: python -m pstats transmission_profile.prof")
    print("  Then: sort cumtime / stats 30")
