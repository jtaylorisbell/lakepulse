"""Collect hardware metrics from macOS using psutil and powermetrics."""

import json
import platform
import subprocess
import time
from datetime import datetime, timezone

import psutil


def _ts() -> int:
    """Epoch microseconds — the format ZeroBus expects for TIMESTAMP columns."""
    return int(datetime.now(timezone.utc).timestamp() * 1_000_000)


def _hostname() -> str:
    return platform.node()


def collect_cpu() -> list[dict]:
    """CPU usage per-core, frequency, and load averages."""
    hostname = _hostname()
    ts = _ts()
    records = []

    # Per-core usage
    per_core = psutil.cpu_percent(percpu=True)
    for i, pct in enumerate(per_core):
        records.append({
            "ts": ts, "hostname": hostname,
            "category": "cpu", "metric": "cpu_percent",
            "value": pct, "unit": "percent",
            "tags": json.dumps({"core": i}),
        })

    # Overall usage
    records.append({
        "ts": ts, "hostname": hostname,
        "category": "cpu", "metric": "cpu_percent_total",
        "value": psutil.cpu_percent(), "unit": "percent",
        "tags": None,
    })

    # Frequency (may not be available on all Macs)
    freq = psutil.cpu_freq()
    if freq:
        records.append({
            "ts": ts, "hostname": hostname,
            "category": "cpu", "metric": "cpu_freq_mhz",
            "value": freq.current, "unit": "mhz",
            "tags": None,
        })

    # Load averages
    load1, load5, load15 = psutil.getloadavg()
    for name, val in [("load_1m", load1), ("load_5m", load5), ("load_15m", load15)]:
        records.append({
            "ts": ts, "hostname": hostname,
            "category": "cpu", "metric": name,
            "value": val, "unit": "load",
            "tags": None,
        })

    return records


def collect_memory() -> list[dict]:
    """Physical and swap memory."""
    hostname = _hostname()
    ts = _ts()
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    return [
        {"ts": ts, "hostname": hostname, "category": "memory", "metric": "memory_used_bytes", "value": vm.used, "unit": "bytes", "tags": None},
        {"ts": ts, "hostname": hostname, "category": "memory", "metric": "memory_total_bytes", "value": vm.total, "unit": "bytes", "tags": None},
        {"ts": ts, "hostname": hostname, "category": "memory", "metric": "memory_percent", "value": vm.percent, "unit": "percent", "tags": None},
        {"ts": ts, "hostname": hostname, "category": "memory", "metric": "swap_used_bytes", "value": sw.used, "unit": "bytes", "tags": None},
        {"ts": ts, "hostname": hostname, "category": "memory", "metric": "swap_percent", "value": sw.percent, "unit": "percent", "tags": None},
    ]


def collect_disk() -> list[dict]:
    """Disk usage and I/O counters."""
    hostname = _hostname()
    ts = _ts()
    records = []

    # Usage for root partition
    usage = psutil.disk_usage("/")
    records.extend([
        {"ts": ts, "hostname": hostname, "category": "disk", "metric": "disk_used_bytes", "value": usage.used, "unit": "bytes", "tags": json.dumps({"mount": "/"})},
        {"ts": ts, "hostname": hostname, "category": "disk", "metric": "disk_total_bytes", "value": usage.total, "unit": "bytes", "tags": json.dumps({"mount": "/"})},
        {"ts": ts, "hostname": hostname, "category": "disk", "metric": "disk_percent", "value": usage.percent, "unit": "percent", "tags": json.dumps({"mount": "/"})},
    ])

    # I/O counters
    io = psutil.disk_io_counters()
    if io:
        records.extend([
            {"ts": ts, "hostname": hostname, "category": "disk", "metric": "disk_read_bytes", "value": io.read_bytes, "unit": "bytes", "tags": None},
            {"ts": ts, "hostname": hostname, "category": "disk", "metric": "disk_write_bytes", "value": io.write_bytes, "unit": "bytes", "tags": None},
        ])

    return records


def collect_network() -> list[dict]:
    """Network I/O counters per interface."""
    hostname = _hostname()
    ts = _ts()
    records = []
    counters = psutil.net_io_counters(pernic=True)
    for iface, stats in counters.items():
        if iface == "lo0":
            continue
        tags = json.dumps({"interface": iface})
        records.extend([
            {"ts": ts, "hostname": hostname, "category": "network", "metric": "net_bytes_sent", "value": stats.bytes_sent, "unit": "bytes", "tags": tags},
            {"ts": ts, "hostname": hostname, "category": "network", "metric": "net_bytes_recv", "value": stats.bytes_recv, "unit": "bytes", "tags": tags},
        ])
    return records


def collect_battery() -> list[dict]:
    """Battery status."""
    hostname = _hostname()
    ts = _ts()
    batt = psutil.sensors_battery()
    if not batt:
        return []
    return [
        {"ts": ts, "hostname": hostname, "category": "battery", "metric": "battery_percent", "value": batt.percent, "unit": "percent", "tags": None},
        {"ts": ts, "hostname": hostname, "category": "battery", "metric": "battery_plugged", "value": 1.0 if batt.power_plugged else 0.0, "unit": "boolean", "tags": None},
    ]


def collect_powermetrics() -> list[dict]:
    """Thermal, fan, and GPU data from macOS powermetrics (requires sudo)."""
    hostname = _hostname()
    ts = _ts()
    records = []

    try:
        result = subprocess.run(
            ["sudo", "powermetrics", "--samplers", "smc", "-n", "1", "-i", "100", "--format", "plist"],
            capture_output=True, timeout=10,
        )
        if result.returncode != 0:
            return []

        import plistlib
        data = plistlib.loads(result.stdout)

        # Thermal pressure
        thermal = data.get("thermal_pressure", "")
        pressure_map = {"nominal": 0, "moderate": 1, "heavy": 2, "critical": 3}
        records.append({
            "ts": ts, "hostname": hostname,
            "category": "thermal", "metric": "thermal_pressure",
            "value": pressure_map.get(thermal.lower(), -1), "unit": "level",
            "tags": json.dumps({"label": thermal}),
        })

        # Fan speeds
        for fan in data.get("fans", []):
            records.append({
                "ts": ts, "hostname": hostname,
                "category": "fan", "metric": "fan_speed_rpm",
                "value": fan.get("fan_rpm", 0), "unit": "rpm",
                "tags": json.dumps({"fan_id": fan.get("fan_id", 0)}),
            })

        # GPU power (if available in SMC data)
        gpu_power = data.get("gpu_power", None)
        if gpu_power is not None:
            records.append({
                "ts": ts, "hostname": hostname,
                "category": "gpu", "metric": "gpu_power_watts",
                "value": gpu_power, "unit": "watts",
                "tags": None,
            })

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass

    return records


def collect_all() -> list[dict]:
    """Collect all available metrics."""
    records = []
    records.extend(collect_cpu())
    records.extend(collect_memory())
    records.extend(collect_disk())
    records.extend(collect_network())
    records.extend(collect_battery())
    records.extend(collect_powermetrics())
    return records
