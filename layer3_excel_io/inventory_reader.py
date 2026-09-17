"""
Layer 3 - Excel inventory import.

Reads the device inventory from a real .xlsx workbook (via openpyxl) so
Layer 1 knows what to check without hardcoding a device list in Python.

Expected columns (header row 1), in any order:
    Hostname | IPAddress | TCPPort | IsLocalHost | DeviceType | ExpectedOS | Location | Notes
"""

from __future__ import annotations

from pathlib import Path

import openpyxl

DEFAULT_INVENTORY_PATH = Path(__file__).resolve().parent.parent / "inventory" / "device_inventory.xlsx"

_REQUIRED_COLUMNS = {"hostname", "ipaddress"}


def _normalize_header(value) -> str:
    return str(value).strip().lower().replace(" ", "").replace("_", "") if value else ""


def load_inventory(path: Path | str = DEFAULT_INVENTORY_PATH) -> list[dict]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Device inventory workbook not found at {path}. "
            "Run inventory/generate_sample_inventory.py to create a sample, "
            "or point --inventory at your own .xlsx file."
        )

    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = workbook.active

    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise ValueError(f"Inventory workbook {path} is empty.")

    header = [_normalize_header(h) for h in rows[0]]
    missing = _REQUIRED_COLUMNS - set(header)
    if missing:
        raise ValueError(f"Inventory workbook {path} is missing required column(s): {missing}")

    devices = []
    for row in rows[1:]:
        if row is None or all(cell is None for cell in row):
            continue
        record = dict(zip(header, row))

        hostname = record.get("hostname")
        ip_address = record.get("ipaddress")
        if not hostname or not ip_address:
            continue

        tcp_port = record.get("tcpport")
        is_local_raw = record.get("islocalhost")

        devices.append({
            "hostname": str(hostname).strip(),
            "ip_address": str(ip_address).strip(),
            "tcp_port": int(tcp_port) if tcp_port else None,
            "is_local_host": str(is_local_raw).strip().lower() in ("true", "yes", "1") if is_local_raw is not None else False,
            "device_type": str(record.get("devicetype") or "").strip(),
            "expected_os": str(record.get("expectedos") or "").strip(),
            "location": str(record.get("location") or "").strip(),
            "notes": str(record.get("notes") or "").strip(),
        })

    if not devices:
        raise ValueError(f"No valid device rows found in {path}.")

    return devices
