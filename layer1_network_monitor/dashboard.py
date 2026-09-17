"""
Layer 1 - Console dashboard.

Renders the current status of every monitored device, combining the live
reachability check (this run) with historical uptime percentage, plus a
one-line summary of that device's Layer 2 diagnostics when available.
"""

from __future__ import annotations

from layer1_network_monitor.network_scanner import CheckResult
from layer1_network_monitor.uptime_tracker import UptimeTracker


def _status_label(reachable: bool) -> str:
    return "UP" if reachable else "DOWN"


def render_dashboard(results: list[CheckResult], tracker: UptimeTracker,
                      layer2_summaries: dict[str, str] | None = None) -> str:
    layer2_summaries = layer2_summaries or {}

    headers = ["STATUS", "HOSTNAME", "IP ADDRESS", "LATENCY", "UPTIME%", "CHECKS", "LAYER 2 SUMMARY"]
    rows = []
    for result in results:
        uptime = tracker.uptime_percent(result.hostname)
        rows.append([
            _status_label(result.reachable),
            result.hostname,
            result.ip_address,
            f"{result.latency_ms} ms" if result.latency_ms is not None else "-",
            f"{uptime}%" if uptime is not None else "-",
            str(tracker.check_count(result.hostname)),
            layer2_summaries.get(result.hostname, "-"),
        ])

    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) if rows else len(headers[i])
              for i in range(len(headers))]

    def fmt_row(row: list[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    lines = [fmt_row(headers), "  ".join("-" * w for w in widths)]
    lines.extend(fmt_row(row) for row in rows)

    up_count = sum(1 for r in results if r.reachable)
    lines.append("")
    lines.append(f"{up_count}/{len(results)} devices UP")

    return "\n".join(lines)


def print_dashboard(results: list[CheckResult], tracker: UptimeTracker,
                     layer2_summaries: dict[str, str] | None = None) -> None:
    print(render_dashboard(results, tracker, layer2_summaries))
