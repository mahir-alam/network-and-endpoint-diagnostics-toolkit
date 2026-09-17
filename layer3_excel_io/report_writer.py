"""
Layer 3 - Excel report export.

Writes a combined status report back to a real .xlsx workbook after each
monitoring run, merging:
    - Layer 1 results: reachability, latency, uptime% history
    - Layer 2 results: OS/hardware specs, disk/memory health, printer tests

into one record-keeping file with two linked sheets.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

DEFAULT_REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"

_HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
_HEADER_FONT = Font(color="FFFFFF", bold=True)


def _write_sheet(ws, headers: list[str], rows: list[list]) -> None:
    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
    for row in rows:
        ws.append(row)
    for col_idx, header in enumerate(headers, start=1):
        width = max(len(str(header)), *(len(str(row[col_idx - 1])) for row in rows)) if rows else len(str(header))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(width + 2, 60)


def write_report(network_rows: list[dict], device_rows: dict[str, dict],
                  output_path: Path | str | None = None) -> Path:
    """
    network_rows: list of dicts with keys hostname, ip_address, status,
        latency_ms, uptime_percent, total_checks, expected_os, device_type,
        location, notes, layer2_health_status
    device_rows: dict keyed by hostname -> the parsed Layer 2 diagnostic
        JSON (from Invoke-DeviceDiagnostics.ps1), only present for devices
        that had local Layer 2 diagnostics run against them.
    """
    output_path = Path(output_path) if output_path else DEFAULT_REPORT_DIR / f"diagnostics_report_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()

    ws_network = wb.active
    ws_network.title = "Network Status (Layer 1)"
    network_headers = [
        "Hostname", "IP Address", "Status", "Latency (ms)", "Uptime %",
        "Total Checks", "Device Type", "Expected OS", "Location",
        "Layer 2 Health", "Notes",
    ]
    network_data = [[
        r["hostname"], r["ip_address"], r["status"], r["latency_ms"],
        r["uptime_percent"], r["total_checks"], r["device_type"],
        r["expected_os"], r["location"], r.get("layer2_health_status", "N/A"),
        r["notes"],
    ] for r in network_rows]
    _write_sheet(ws_network, network_headers, network_data)

    ws_device = wb.create_sheet("Device Diagnostics (Layer 2)")
    device_headers = [
        "Hostname", "Health Status", "OS", "OS Version", "Manufacturer",
        "Model", "CPU", "Total Memory (GB)", "Free Memory (MB)",
        "Disk Summary", "Installed Software Count", "Printer Count",
        "Printer Test Results", "USB Peripheral Count", "Warnings", "Checked At",
    ]
    device_data = []
    for hostname, diag in device_rows.items():
        info = diag.get("DeviceInfo", {})
        peripherals = diag.get("PeripheralInfo", {})
        disks = info.get("Disks") or []
        if isinstance(disks, dict):
            disks = [disks]
        disk_summary = "; ".join(
            f"{d.get('DeviceID')} {d.get('FreeGB')}GB free / {d.get('SizeGB')}GB ({d.get('PercentFree')}%)"
            for d in disks
        )
        printers = peripherals.get("Printers") or []
        if isinstance(printers, dict):
            printers = [printers]
        printer_summary = "; ".join(
            f"{p.get('Name')}: {p.get('PrinterStatus')} / {p.get('TestPageResult')}"
            for p in printers
        )
        device_data.append([
            hostname,
            diag.get("HealthStatus"),
            info.get("OS"),
            info.get("OSVersion"),
            info.get("Manufacturer"),
            info.get("Model"),
            info.get("CPU"),
            info.get("TotalMemoryGB"),
            info.get("FreePhysicalMemoryMB"),
            disk_summary,
            info.get("InstalledSoftwareCount"),
            peripherals.get("PrinterCount"),
            printer_summary,
            peripherals.get("USBPeripheralCount"),
            "; ".join(diag.get("Warnings") or []),
            diag.get("CheckedAt"),
        ])
    _write_sheet(ws_device, device_headers, device_data)

    wb.save(output_path)
    return output_path
