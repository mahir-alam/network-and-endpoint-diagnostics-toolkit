"""
Main entry point: ties Layer 1 (network), Layer 2 (device), and Layer 3
(Excel) together into one monitoring run.

For every device in the inventory:
  1. Run a real Layer 1 reachability check (ICMP ping or TCP connect).
  2. Log the result to the uptime history database.
  3. If the device is flagged IsLocalHost=True in the inventory, also run
     the real Layer 2 PowerShell diagnostics (device info + printer test)
     against this machine via subprocess - this is the integration point:
     "is this device reachable" and "what's going on with this device"
     are joined per-device, not two disconnected tools.
  4. Print a combined console dashboard.
  5. Export a combined .xlsx report merging Layer 1 + Layer 2 results.

Usage:
    python -m integration.run_diagnostics [--inventory PATH] [--skip-printer-test]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from layer1_network_monitor.dashboard import print_dashboard, render_dashboard
from layer1_network_monitor.network_scanner import scan_inventory
from layer1_network_monitor.uptime_tracker import UptimeTracker
from layer3_excel_io.inventory_reader import load_inventory
from layer3_excel_io.report_writer import write_report

REPO_ROOT = Path(__file__).resolve().parent.parent
PS_DIAGNOSTICS_SCRIPT = REPO_ROOT / "layer2_device_diagnostics" / "Invoke-DeviceDiagnostics.ps1"


def run_layer2_diagnostics(skip_printer_test: bool = True) -> dict | None:
    """Invoke the real PowerShell Layer 2 diagnostics script and parse its JSON."""
    cmd = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(PS_DIAGNOSTICS_SCRIPT),
    ]
    if skip_printer_test:
        cmd.append("-SkipPrinterTest")

    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        print("  [Layer 2] powershell.exe not found - skipping device diagnostics.", file=sys.stderr)
        return None

    if completed.returncode != 0:
        print(f"  [Layer 2] PowerShell diagnostics failed: {completed.stderr.strip()}", file=sys.stderr)
        return None

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        print("  [Layer 2] Could not parse PowerShell diagnostics output as JSON.", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Network & device diagnostics monitoring run")
    parser.add_argument("--inventory", type=Path, default=None,
                         help="Path to device_inventory.xlsx (defaults to inventory/device_inventory.xlsx)")
    parser.add_argument("--run-printer-test", action="store_true",
                         help="Actually submit a physical test page to installed printers (default: skip)")
    parser.add_argument("--report-out", type=Path, default=None,
                         help="Output path for the combined .xlsx report")
    parser.add_argument("--timeout", type=float, default=2.0, help="Per-device network check timeout (seconds)")
    args = parser.parse_args()

    inventory_kwargs = {"path": args.inventory} if args.inventory else {}
    devices = load_inventory(**inventory_kwargs)
    print(f"Loaded {len(devices)} devices from inventory.\n")

    print("Running Layer 1 network reachability checks...")
    results = scan_inventory(devices, timeout_s=args.timeout)

    tracker = UptimeTracker()
    tracker.record_all(results)

    device_by_hostname = {d["hostname"]: d for d in devices}
    layer2_results: dict[str, dict] = {}
    layer2_summaries: dict[str, str] = {}

    for result in results:
        device = device_by_hostname[result.hostname]
        if device["is_local_host"]:
            print(f"  [Layer 2] Running device diagnostics for '{result.hostname}' (local host)...")
            diag = run_layer2_diagnostics(skip_printer_test=not args.run_printer_test)
            if diag:
                layer2_results[result.hostname] = diag
                layer2_summaries[result.hostname] = f"{diag['HealthStatus']} ({len(diag.get('Warnings', []))} warning(s))"

    print()
    print_dashboard(results, tracker, layer2_summaries)

    network_rows = []
    for result in results:
        device = device_by_hostname[result.hostname]
        network_rows.append({
            "hostname": result.hostname,
            "ip_address": result.ip_address,
            "status": "UP" if result.reachable else "DOWN",
            "latency_ms": result.latency_ms,
            "uptime_percent": tracker.uptime_percent(result.hostname),
            "total_checks": tracker.check_count(result.hostname),
            "device_type": device["device_type"],
            "expected_os": device["expected_os"],
            "location": device["location"],
            "layer2_health_status": layer2_results.get(result.hostname, {}).get("HealthStatus", "N/A"),
            "notes": device["notes"],
        })

    report_path = write_report(network_rows, layer2_results, output_path=args.report_out)
    print(f"\nCombined report written to: {report_path}")

    tracker.close()


if __name__ == "__main__":
    main()
