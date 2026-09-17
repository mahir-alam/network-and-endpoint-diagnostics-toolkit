"""
Layer 1 - Network monitoring.

Real TCP/IP reachability checks against devices in the inventory:
  - ICMP reachability via the OS ping utility (cross-platform)
  - Optional TCP port checks via raw sockets (socket.create_connection)

No third-party ping libraries are used - this shells out to the platform's
native `ping` binary (this is the standard, portable way to send ICMP echo
requests from Python without requiring raw-socket / admin privileges on
Windows) and uses the stdlib `socket` module directly for TCP checks.
"""

from __future__ import annotations

import platform
import re
import socket
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone


_IS_WINDOWS = platform.system().lower() == "windows"

# Windows ping reports round-trip time as "time=12ms" or "time<1ms";
# Linux/macOS ping reports it as "time=12.3 ms".
_RTT_PATTERN = re.compile(r"time[=<]\s*([\d.]+)\s*ms", re.IGNORECASE)


@dataclass
class CheckResult:
    hostname: str
    ip_address: str
    reachable: bool
    method: str
    latency_ms: float | None
    detail: str
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict:
        return {
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "reachable": self.reachable,
            "method": self.method,
            "latency_ms": self.latency_ms,
            "detail": self.detail,
            "checked_at": self.checked_at,
        }


def ping_host(ip_address: str, timeout_s: float = 2.0) -> tuple[bool, float | None, str]:
    """Send a single real ICMP echo request via the OS ping command.

    Returns (reachable, latency_ms, detail).
    """
    if _IS_WINDOWS:
        timeout_ms = int(timeout_s * 1000)
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), ip_address]
    else:
        cmd = ["ping", "-c", "1", "-W", str(int(max(1, timeout_s))), ip_address]

    try:
        completed = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_s + 2,
            text=True,
        )
    except subprocess.TimeoutExpired:
        return False, None, "ping process timed out"
    except FileNotFoundError:
        return False, None, "ping utility not found on this system"

    output = completed.stdout or ""
    reachable = completed.returncode == 0

    latency_ms = None
    match = _RTT_PATTERN.search(output)
    if match:
        latency_ms = float(match.group(1))

    if reachable:
        detail = f"ICMP echo reply ({latency_ms} ms)" if latency_ms is not None else "ICMP echo reply"
    else:
        detail = "no ICMP echo reply (host unreachable, filtered, or offline)"

    return reachable, latency_ms, detail


def tcp_check(ip_address: str, port: int, timeout_s: float = 2.0) -> tuple[bool, float | None, str]:
    """Attempt a real TCP three-way handshake against ip_address:port."""
    start = time.perf_counter()
    try:
        with socket.create_connection((ip_address, port), timeout=timeout_s):
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            return True, elapsed_ms, f"TCP connect succeeded on port {port}"
    except (socket.timeout, TimeoutError):
        return False, None, f"TCP connect to port {port} timed out"
    except ConnectionRefusedError:
        return False, None, f"TCP connect to port {port} refused (host up, port closed)"
    except OSError as exc:
        return False, None, f"TCP connect to port {port} failed: {exc}"


def check_device(hostname: str, ip_address: str, tcp_port: int | None = None,
                  timeout_s: float = 2.0) -> CheckResult:
    """Run the appropriate real reachability check(s) for one inventory device.

    If a TCP port is specified in the inventory, a TCP connect check is used
    (useful for hosts/firewalls that drop ICMP but still serve a service).
    Otherwise a real ICMP ping is performed.
    """
    if tcp_port:
        reachable, latency_ms, detail = tcp_check(ip_address, tcp_port, timeout_s)
        method = "tcp"
        if not reachable:
            # Fall back to ICMP so a closed monitoring port doesn't mask a live host
            icmp_reachable, icmp_latency, icmp_detail = ping_host(ip_address, timeout_s)
            if icmp_reachable:
                reachable, latency_ms, detail, method = icmp_reachable, icmp_latency, icmp_detail, "icmp (tcp fallback)"
    else:
        reachable, latency_ms, detail = ping_host(ip_address, timeout_s)
        method = "icmp"

    return CheckResult(
        hostname=hostname,
        ip_address=ip_address,
        reachable=reachable,
        method=method,
        latency_ms=latency_ms,
        detail=detail,
    )


def scan_inventory(devices: list[dict], timeout_s: float = 2.0) -> list[CheckResult]:
    """Run real reachability checks against every device in the inventory list.

    `devices` is a list of dicts as produced by layer3_excel_io.inventory_reader,
    each with at least 'hostname' and 'ip_address' keys and an optional 'tcp_port'.
    """
    results = []
    for device in devices:
        result = check_device(
            hostname=device["hostname"],
            ip_address=device["ip_address"],
            tcp_port=device.get("tcp_port") or None,
            timeout_s=timeout_s,
        )
        results.append(result)
    return results
