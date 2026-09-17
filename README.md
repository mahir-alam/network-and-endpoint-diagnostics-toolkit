# Network & Device Diagnostics Toolkit

A three-layer diagnostics tool for IT support/help desk work: **Layer 1**
checks whether devices are reachable on the network (Python, real TCP/IP),
**Layer 2** checks whether a device is actually healthy (PowerShell, real
system/hardware queries), and **Layer 3** ties both to a device inventory
and a combined report (Excel). A companion Cisco Packet Tracer topology
demonstrates real switch/VLAN configuration skills the other two layers
don't touch.

## Why this project

Built for the EVR Desktop Support Co-op posting (Sparwood, BC, January
2027 start), specifically this line from the job description:

> "Collaborate with help desk and network operations teams to determine
> and resolve end user issues"

This started as two separate planned projects — one covering
network-layer connectivity monitoring and Cisco switch/VLAN
configuration, the other covering device-level diagnostics and
printer/peripheral testing via PowerShell — and was combined because
that's how real help-desk monitoring tooling is actually architected: you
check whether a device is *reachable* (network layer) and, separately,
whether it's *healthy* (device layer), in one dashboard rather than two
disconnected tools.

Two other projects already exist alongside this one on the same resume:
an IT Help Desk Ticketing & Asset Dashboard (live ITSM system) and a
Fleet Asset Tracking & Predictive Analytics platform (Python, SQL, Power
BI, Excel, PowerShell). This project's job is specifically to cover the
network-diagnostics-plus-Cisco-hardware ground neither of those touches —
Power BI is deliberately not used here since the Fleet project already
covers it.

## Honesty notes (read this before the feature list)

- This is a **simulated, educational** network environment built in Cisco
  Packet Tracer — not real industrial or enterprise hardware, and no
  claim is made otherwise.
- **No named commercial/industrial product** (WhatsUp Gold, SCADA, PLCs,
  RTUs, etc.) is used or claimed. All monitoring code here is
  custom-written.
- This is **solo student work** — no claim of an actual help desk or
  network operations team is made.
- Every PowerShell cmdlet used here was verified to exist and to actually
  run against a real Windows machine during development (see
  [What was actually verified](#what-was-actually-verified) below) —
  none are guessed syntax.
- **The Cisco Packet Tracer `.pkt` file and its exported CLI evidence are
  not yet in this repo.** Packet Tracer is a GUI desktop application that
  can't be installed, driven, or exported from an automated coding
  environment. The topology design and the actual Cisco IOS configuration
  commands are fully written and are real, correct syntax — see
  [`packet_tracer/`](packet_tracer/) — but building the topology in the
  Packet Tracer application, pasting in the provided configs, and
  exporting the `.pkt` + `show running-config` output is a manual step
  documented in [`packet_tracer/README.md`](packet_tracer/README.md) that
  still needs to be done by hand.

## Tech stack

Python, PowerShell, TCP/IP, Cisco Packet Tracer, Excel — confirmed, all
five doing real, load-bearing work (see table below).

| Tool | What it actually does here |
|------|------------------------------|
| **Python** | Runs the Layer 1 reachability checks, uptime logging, dashboard rendering, and orchestrates calling into Layer 2/3. |
| **PowerShell** | Executes real device-info pulls (`Get-ComputerInfo`, `Get-CimInstance`) and a real printer test-page job (`Win32_Printer.PrintTestPage` via `Invoke-CimMethod`) plus peripheral enumeration (`Get-PnpDevice`). |
| **TCP/IP** | Real ICMP pings (via the OS `ping` binary) and real TCP socket connects (`socket.create_connection`) — see `layer1_network_monitor/network_scanner.py`. |
| **Cisco Packet Tracer** | A designed, real switch/VLAN topology (3 switches, 2 VLANs + management VLAN, inter-VLAN routing, a segmentation ACL) with genuine Cisco IOS CLI configs — see [Honesty notes](#honesty-notes-read-this-before-the-feature-list) for what's still manual. |
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

For every device in the inventory, Layer 1 runs a real reachability
check. Any device flagged `IsLocalHost=True` in the inventory (by
default, just the machine running the toolkit) *also* gets the full
Layer 2 PowerShell diagnostic run against it, and both results land in
the same dashboard row and the same report — so "is this device
reachable" and "what's actually wrong with it" are joined per-device,
not two disconnected tool outputs bundled in one repo.

### Why the Packet Tracer topology and the live network check use different IP ranges

The sample inventory (`inventory/device_inventory.xlsx`) mixes two kinds
of rows on purpose:

1. **Real, reachable targets** — `127.0.0.1` (this machine),
   the local network's default gateway, and two public DNS resolvers
   (`1.1.1.1`, `8.8.8.8`). These show **UP** when you actually run the
   toolkit, proving the Python/TCP-IP layer genuinely performs live
   checks rather than returning canned data.
2. **Addresses matching the Packet Tracer topology** (`192.168.10.x`,
   `192.168.20.x`, `192.168.99.x` — see
   [`packet_tracer/topology_diagram.md`](packet_tracer/topology_diagram.md)).
   These correctly show **DOWN** when the toolkit runs outside Packet
   Tracer, because Packet Tracer's simulated network isn't bridged to
   the host machine's real NIC. They're included so the inventory
   visibly mirrors the Cisco topology's addressing scheme, *not* to
   pretend the Python tool reaches into the simulator — it doesn't, and
   this README isn't claiming it does.

## Feature spec vs. what was built

### Layer 1 — Network monitoring (`layer1_network_monitor/`)
- [x] Real ICMP ping checks (`network_scanner.ping_host`, shells out to the
      OS `ping` binary and parses real round-trip time)
- [x] Real TCP socket checks (`network_scanner.tcp_check`, stdlib `socket`)
- [x] Uptime/downtime history logged to SQLite (`uptime_tracker.py`),
      uptime % computed from real accumulated check history
- [x] Console dashboard (`dashboard.py`) showing live status, latency,
      uptime %, and a Layer 2 health summary per device
- [ ] Real Cisco topology export (`.pkt` + CLI evidence) — **not done,
      see Honesty notes**; the design and IOS configs are done

### Layer 2 — Device-level diagnostics (`layer2_device_diagnostics/`)
- [x] `Get-DeviceInfo.ps1` — OS, version, architecture, manufacturer,
      model, CPU, total/free memory, per-disk free space, installed
      software list (real registry uninstall-key enumeration), last boot time
- [x] `Test-PrinterPeripheral.ps1` — enumerates installed printers, submits
      a **real** test-page spool job via `Win32_Printer.PrintTestPage`,
      reports live printer status and queue depth, enumerates USB
      peripherals via `Get-PnpDevice`
- [x] `Invoke-DeviceDiagnostics.ps1` — orchestrates both scripts and
      applies real threshold-based health rules (disk <15%/<5% free,
      memory <15%/<5% free, non-normal printer status) to produce a
      Healthy/Warning/Critical verdict — not a stub value

### Layer 3 — Excel inventory & reporting (`layer3_excel_io/`, `inventory/`)
- [x] Imports device inventory from a real `.xlsx` (`inventory_reader.py`,
      via `openpyxl`) — hostnames, IPs, expected OS, local-host flag, notes
- [x] Exports a combined `.xlsx` report after each run (`report_writer.py`)
      with a "Network Status (Layer 1)" sheet and a "Device Diagnostics
      (Layer 2)" sheet, merged per device

### Integration
- [x] Local-host devices get both layers joined in the dashboard and report

## What was actually verified

Every cmdlet and code path below was run for real on a Windows 11 machine
during development, not just written and assumed to work:

- `Get-ComputerInfo`, `Get-CimInstance` (`Win32_OperatingSystem`,
  `Win32_ComputerSystem`, `Win32_Processor`, `Win32_LogicalDisk`,
  `Win32_PhysicalMemory`) — confirmed present and returned real hardware
  data (actual CPU model, memory, disk free space).
- `Get-Printer`, `Get-PrintJob`, `Get-PnpDevice` — confirmed present;
  ran against a real installed printer and correctly detected and
  reported it as **Offline** (a genuine health finding, not a canned
  result).
- `Win32_Printer.PrintTestPage` via `Invoke-CimMethod` — confirmed the
  method exists on this system's WMI class (`Get-CimClass -ClassName
  Win32_Printer` lists it).
- The full `python -m integration.run_diagnostics` pipeline was run
  end-to-end: it loaded the sample inventory, pinged real local/public
  hosts (got real latencies), correctly showed the Packet-Tracer-only
  addresses as unreachable, ran the PowerShell diagnostics subprocess,
  parsed its JSON, logged everything to SQLite, printed the dashboard,
  and wrote a real, readable `.xlsx` report with both sheets populated.

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
- **Live deployed link:** not applicable — this monitors local/simulated
  network devices and desktop Packet Tracer files, not a hosted service.
- **Fallback evidence:** the code itself runs and is demonstrated above;
  once the manual Packet Tracer step in
  [`packet_tracer/README.md`](packet_tracer/README.md) is completed, that
  folder will also contain the `.pkt` file, switches' own
  `show running-config` output, and screenshots proving the VLAN
  segmentation actually works (not just that it's configured).

## Repo structure

```
inventory/                    Layer 3 sample input (.xlsx) + generator script
layer1_network_monitor/       Python — ping/TCP checks, uptime log, dashboard
layer2_device_diagnostics/    PowerShell — device info, printer/peripheral tests
layer3_excel_io/              Python — .xlsx import/export
integration/                  Main entry point tying all three layers together
packet_tracer/                Topology design, real Cisco IOS configs, build guide
```

## Known simplifications / weaker areas (read before treating this as finished)

- **Layer 2 diagnostics only run against the local machine by default.**
  PowerShell Remoting (`Invoke-Command -ComputerName`) would extend this
  to other machines on the network, but that requires WinRM trust
  configuration between machines that wasn't available to test here, so
  it's not implemented or claimed as working — the `IsLocalHost` flag in
  the inventory is the honest boundary of what's actually demonstrated.
- **Packet Tracer evidence is design + configs only, not yet the actual
  `.pkt` export** — see Honesty notes above.
