# Network & Device Diagnostics Toolkit

A three-layer diagnostics tool for IT support work.

- **Layer 1** checks whether devices are reachable on the network (Python, real TCP/IP).
- **Layer 2** checks whether a device is actually healthy (PowerShell, real system/hardware queries).
- **Layer 3** ties both to a device inventory and a combined report (Excel).
- A Cisco Packet Tracer topology demonstrates switch/VLAN configuration, separate from the other three layers.

## Why this project

Built for the EVR Desktop Support Co-op posting (Sparwood, BC, January 2027 start), against this line in the job description:

> "Collaborate with help desk and network operations teams to determine and resolve end user issues"

It combines two originally separate ideas — network-layer connectivity monitoring plus Cisco switch/VLAN configuration, and device-level diagnostics plus printer/peripheral testing via PowerShell — because that's how real help-desk monitoring tools are built: check whether a device is reachable, and separately whether it's healthy, in one dashboard.

Two other projects sit alongside this one on the same resume: an IT Help Desk Ticketing & Asset Dashboard, and a Fleet Asset Tracking & Predictive Analytics platform (which already covers Power BI). This project covers the network-diagnostics and Cisco-hardware ground those two don't.

## Honesty notes

- This is a simulated, educational network built in Cisco Packet Tracer, not real industrial or enterprise hardware.
- No named commercial/industrial product (WhatsUp Gold, SCADA, PLCs, RTUs) is used or claimed. All monitoring code here is custom-written.
- This is solo student work. No claim of an actual help desk or network operations team is made.
- Every PowerShell cmdlet used here was run against a real Windows machine during development — see [What was verified](#what-was-verified).

## Tech stack

| Tool | What it does here |
|------|--------------------|
| **Python** | Runs the Layer 1 reachability checks, uptime logging, dashboard rendering, and orchestrates Layer 2/3. |
| **PowerShell** | Pulls real device info (`Get-ComputerInfo`, `Get-CimInstance`) and runs a real printer test-page job (`Win32_Printer.PrintTestPage`) plus peripheral enumeration (`Get-PnpDevice`). |
| **TCP/IP** | Real ICMP pings (via the OS `ping` binary) and real TCP socket connects (`socket.create_connection`). See `layer1_network_monitor/network_scanner.py`. |
| **Cisco Packet Tracer** | A 3-switch, 2-VLAN topology with inter-VLAN routing and a segmentation ACL. See `packet_tracer/`. |
| **Excel** | Real `.xlsx` read (device inventory) and write (combined status report) via `openpyxl` — not CSVs relabeled, not Power BI. |

## Architecture

```
inventory/device_inventory.xlsx
            │  (Layer 3 import)
            ▼
┌───────────────────────────┐
│ integration/run_diagnostics.py │
└─────────────┬─────────────┘
              │
   ┌──────────┴───────────┐
   ▼                       ▼
Layer 1 (Python)      Layer 2 (PowerShell, local host only)
- ICMP ping / TCP      - Get-DeviceInfo.ps1
  socket checks        - Test-PrinterPeripheral.ps1
- SQLite uptime log    - Invoke-DeviceDiagnostics.ps1 (orchestrator)
- Console dashboard      → JSON on stdout, parsed by Python
   │                       │
   └──────────┬────────────┘
              ▼
   reports/diagnostics_report_<timestamp>.xlsx
   (Layer 3 export — Network Status + Device Diagnostics sheets)
```

### The integration point

For every device in the inventory, Layer 1 runs a real reachability check. Any device flagged `IsLocalHost=True` (by default, just the machine running the toolkit) also gets the full Layer 2 PowerShell diagnostic run against it. Both results land in the same dashboard row and the same report — reachability and health are joined per device, not two separate tool outputs.

### Why the Packet Tracer topology and the live network check use different IP ranges

The sample inventory (`inventory/device_inventory.xlsx`) mixes two kinds of rows:

1. **Real, reachable targets** — `127.0.0.1` (this machine), the local network's default gateway, and two public DNS resolvers (`1.1.1.1`, `8.8.8.8`). These show **UP** when the toolkit runs, since the Python/TCP-IP layer performs live checks, not canned data.
2. **Addresses matching the Packet Tracer topology** (`192.168.10.x`, `192.168.20.x`, `192.168.99.x` — see `packet_tracer/topology_diagram.md`). These show **DOWN** when the toolkit runs outside Packet Tracer, because Packet Tracer's simulated network isn't bridged to the host machine's real NIC. They're included so the inventory mirrors the Cisco topology's addressing scheme — the Python tool does not reach into the simulator.

## Feature spec vs. what was built

### Layer 1 — Network monitoring (`layer1_network_monitor/`)
- [x] Real ICMP ping checks (`network_scanner.ping_host`, shells out to the OS `ping` binary and parses real round-trip time)
- [x] Real TCP socket checks (`network_scanner.tcp_check`, stdlib `socket`)
- [x] Uptime/downtime history logged to SQLite (`uptime_tracker.py`), uptime % computed from accumulated check history
- [x] Console dashboard (`dashboard.py`) showing live status, latency, uptime %, and a Layer 2 health summary per device

### Layer 2 — Device-level diagnostics (`layer2_device_diagnostics/`)
- [x] `Get-DeviceInfo.ps1` — OS, version, architecture, manufacturer, model, CPU, total/free memory, per-disk free space, installed software list, last boot time
- [x] `Test-PrinterPeripheral.ps1` — enumerates installed printers, submits a real test-page spool job via `Win32_Printer.PrintTestPage`, reports live printer status and queue depth, enumerates USB peripherals via `Get-PnpDevice`
- [x] `Invoke-DeviceDiagnostics.ps1` — orchestrates both scripts and applies threshold-based health rules (disk/memory free-space bands, non-normal printer status) to produce a Healthy/Warning/Critical verdict

### Layer 3 — Excel inventory & reporting (`layer3_excel_io/`, `inventory/`)
- [x] Imports device inventory from a real `.xlsx` (`inventory_reader.py`, via `openpyxl`)
- [x] Exports a combined `.xlsx` report after each run (`report_writer.py`), with a Network Status sheet and a Device Diagnostics sheet, merged per device

### Integration
- [x] Local-host devices get both layers joined in the dashboard and report

### Cisco Packet Tracer (`packet_tracer/`)
- [x] Topology design and addressing scheme (`topology_diagram.md`): 3 switches, 2 VLANs plus a management VLAN, inter-VLAN routing, a segmentation ACL
- [x] Cisco IOS configuration commands for all three switches (`configs/*.txt`)
- [x] Saved Packet Tracer project (`network-topology.pkz`)
- [x] `show running-config` output captured from all three switches (`configs/*_running-config.txt`)
- [x] Screenshot of ping tests run from PC3 against VLAN 10 and VLAN 20 hosts (`segmentation-test-evidence.png`)

## What was verified

Run for real on a Windows 11 machine during development, not just written and assumed to work:

- `Get-ComputerInfo`, `Get-CimInstance` (`Win32_OperatingSystem`, `Win32_ComputerSystem`, `Win32_Processor`, `Win32_LogicalDisk`, `Win32_PhysicalMemory`) — returned real hardware data.
- `Get-Printer`, `Get-PrintJob`, `Get-PnpDevice` — ran against a real installed printer and correctly detected and reported it as Offline.
- `Win32_Printer.PrintTestPage` via `Invoke-CimMethod` — confirmed the method exists on this system's WMI class.
- The full `python -m integration.run_diagnostics` pipeline was run end-to-end: loaded the sample inventory, pinged real local/public hosts, correctly showed the Packet-Tracer-only addresses as unreachable, ran the PowerShell diagnostics subprocess, parsed its JSON, logged everything to SQLite, printed the dashboard, and wrote a readable `.xlsx` report with both sheets populated.

## Running it

```powershell
pip install -r requirements.txt

# (optional) regenerate the sample inventory
python inventory/generate_sample_inventory.py

# run a full monitoring pass (dashboard + Excel report)
python -m integration.run_diagnostics

# actually submit a physical test page to installed printers (off by default)
python -m integration.run_diagnostics --run-printer-test

# point at your own inventory file
python -m integration.run_diagnostics --inventory path\to\your_inventory.xlsx
```

Output:
- Console dashboard of all devices' current status
- `logs/uptime_history.db` — SQLite history (gitignored, machine-specific)
- `reports/diagnostics_report_<timestamp>.xlsx` — combined report (gitignored, machine-specific)

## Verifiability

- **GitHub repo:** this one.
- **Live deployed link:** not applicable — this monitors local/simulated network devices and desktop Packet Tracer files, not a hosted service.
- **Evidence:** the Python/PowerShell/Excel pipeline runs end-to-end, as described above. `packet_tracer/` holds the topology file, the IOS config scripts, each switch's own `show running-config` output, and a screenshot from testing the topology in Packet Tracer.

## Repo structure

```
inventory/                    Layer 3 sample input (.xlsx) + generator script
layer1_network_monitor/       Python — ping/TCP checks, uptime log, dashboard
layer2_device_diagnostics/    PowerShell — device info, printer/peripheral tests
layer3_excel_io/              Python — .xlsx import/export
integration/                  Main entry point tying all three layers together
packet_tracer/                Topology, Cisco IOS configs, running-config exports, screenshot
```

## Known simplifications

- **Layer 2 diagnostics only run against the local machine by default.** PowerShell Remoting (`Invoke-Command -ComputerName`) would extend this to other machines, but that requires WinRM trust configuration between machines that wasn't available to test here. The `IsLocalHost` flag in the inventory is the boundary of what's demonstrated.
