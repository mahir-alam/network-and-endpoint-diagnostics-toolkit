"""
Generates the sample device_inventory.xlsx checked into this repo.

Run this again to regenerate the sample workbook after editing the DEVICES
list below. This is a one-time setup helper, not part of the monitoring
run itself - the toolkit only ever *reads* device_inventory.xlsx at runtime
(see layer3_excel_io/inventory_reader.py).

The inventory intentionally mixes two kinds of targets so the honesty of
the demo is visible in the data itself:

  1. Real, reachable local-network targets (localhost, this machine's
     default gateway, public DNS resolvers) - these will show UP when the
     toolkit is actually run, proving the Python/TCP-IP layer genuinely
     works end to end.
  2. Addresses matching the Cisco Packet Tracer topology in
     packet_tracer/ (see packet_tracer/topology_diagram.md) - these are
     simulated devices inside Packet Tracer, which is not bridged to this
     machine's real NIC, so they will correctly show DOWN/unreachable when
     run outside Packet Tracer. They're included to mirror the addressing
     scheme used in the switch/VLAN configs, not to fake connectivity into
     the simulator.
"""

from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill

OUTPUT_PATH = Path(__file__).resolve().parent / "device_inventory.xlsx"

HEADERS = [
    "Hostname", "IPAddress", "TCPPort", "IsLocalHost", "DeviceType",
    "ExpectedOS", "Location", "Notes",
]

# NOTE: 192.168.1.x values below reflect a real home LAN (private RFC1918
# range) captured during development - update Default-Gateway / This-PC to
# match whatever network you run the toolkit on.
DEVICES = [
    ("This-PC", "127.0.0.1", None, True, "Local Workstation", "Windows 11",
     "Home Office", "Loopback - this machine. Full Layer 2 diagnostics run here."),
    ("Default-Gateway", "192.168.1.254", None, False, "Router/Gateway", "N/A",
     "Home Office", "Real local network gateway - ICMP reachability only (no Layer 2 access)."),
    ("Public-DNS-Cloudflare", "1.1.1.1", None, False, "External Test Target", "N/A",
     "Internet", "Real external host used to prove outbound reachability checks work."),
    ("Public-DNS-Google", "8.8.8.8", None, False, "External Test Target", "N/A",
     "Internet", "Real external host, secondary reachability reference point."),
    ("PT-DistSwitch1-Mgmt", "192.168.99.1", None, False, "Simulated - Packet Tracer Switch", "Cisco IOS",
     "Packet Tracer Topology", "Matches packet_tracer configs/DistSwitch1.txt VLAN99 mgmt SVI. "
     "Expected DOWN outside Packet Tracer - PT is not bridged to this host's NIC."),
    ("PT-PC1-VLAN10", "192.168.10.10", None, False, "Simulated - Packet Tracer End Device", "Windows (simulated)",
     "Packet Tracer Topology", "Matches VLAN 10 (Staff) addressing in the PT topology. Expected DOWN outside PT."),
    ("PT-PC2-VLAN20", "192.168.20.10", None, False, "Simulated - Packet Tracer End Device", "Windows (simulated)",
     "Packet Tracer Topology", "Matches VLAN 20 (Guest) addressing in the PT topology. Expected DOWN outside PT."),
]


def build_workbook() -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Device Inventory"

    ws.append(HEADERS)
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for col_idx in range(1, len(HEADERS) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font

    for device in DEVICES:
        ws.append(list(device))

    widths = [18, 16, 9, 12, 32, 16, 22, 90]
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(row=1, column=idx).column_letter].width = width

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUTPUT_PATH)
    print(f"Wrote sample inventory: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_workbook()
