# Cisco Packet Tracer Topology — Build Guide

**Status: configs and design are done; the `.pkt` file and captured CLI
output are not in this repo yet.** Packet Tracer is a GUI desktop
application — Claude Code cannot install it, drive its UI, or produce a
real `.pkt` file (a proprietary binary format), so that last step has to
be done by hand, once, by whoever owns this repo. Everything up to that
point (topology design, addressing, and the actual Cisco IOS configuration
commands) is done and is real, verifiable Cisco CLI syntax — see
[`topology_diagram.md`](topology_diagram.md) for the design and
[`configs/`](configs/) for the exact commands.

## What you need

- [Cisco Packet Tracer](https://www.netacad.com/courses/packet-tracer) (free from Cisco Networking Academy — requires a free NetAcad account)

## Steps

1. **Open Packet Tracer** and start a new topology.

2. **Place devices** (drag from the device panel at the bottom):
   - 1x **Catalyst 3560** (multilayer switch) → rename to `DistSwitch1`
   - 2x **Catalyst 2960** (switch) → rename to `AccessSwitch1`, `AccessSwitch2`
   - 4x **PC** → rename to `PC1`, `PC2`, `PC3`, `PC4`

   (Rename by clicking the device, then the text label under it.)

3. **Cable it up** using **Copper Straight-Through** cables:
   - `DistSwitch1` FastEthernet0/1 ↔ `AccessSwitch1` FastEthernet0/1
   - `DistSwitch1` FastEthernet0/2 ↔ `AccessSwitch2` FastEthernet0/1
   - `AccessSwitch1` FastEthernet0/2 ↔ `PC1`
   - `AccessSwitch1` FastEthernet0/12 ↔ `PC2`
   - `AccessSwitch2` FastEthernet0/2 ↔ `PC3`
   - `AccessSwitch2` FastEthernet0/12 ↔ `PC4`

   See [`topology_diagram.md`](topology_diagram.md) for the full layout.

4. **Configure each switch** by clicking it → **CLI** tab, then paste in
   the matching file from [`configs/`](configs/) line by line (or in small
   blocks — Packet Tracer's CLI can choke on pasting very large blocks at
   once, so if you hit errors, paste it in 10–15 line chunks):
   - `DistSwitch1` → `configs/DistSwitch1.txt`
   - `AccessSwitch1` → `configs/AccessSwitch1.txt`
   - `AccessSwitch2` → `configs/AccessSwitch2.txt`

5. **Configure the PCs** — click each PC → **Desktop** tab → **IP
   Configuration**, and set (Static):

   | PC  | IP Address    | Subnet Mask     | Default Gateway |
   |-----|---------------|-----------------|------------------|
   | PC1 | 192.168.10.10 | 255.255.255.0   | 192.168.10.1     |
   | PC2 | 192.168.20.10 | 255.255.255.0   | 192.168.20.1     |
   | PC3 | 192.168.10.11 | 255.255.255.0   | 192.168.10.1     |
   | PC4 | 192.168.20.11 | 255.255.255.0   | 192.168.20.1     |

6. **Verify it actually works** (this is the part that proves the configs
   are real, not just typed-in and hoped-for):
   - PC1 → PC3 ping should **succeed** (same VLAN, different switch).
   - PC1 → PC2 ping should **succeed** (different VLANs, routed through
     DistSwitch1's SVIs).
   - PC2 → PC1 ping should **fail** (blocked by the `GUEST-RESTRICT` ACL —
     confirms VLAN 20 is actually being restricted from VLAN 10, not just
     labeled differently).
   - On `DistSwitch1`, run `show vlan brief`, `show ip interface brief`,
     and `show access-lists` and confirm the output matches the config.

7. **Capture the evidence** and drop it into this folder / this repo:
   - Save the topology: **File → Save As** → `packet_tracer/topology.pkt`
   - On each switch's CLI, run `show running-config` and paste/save the
     real output into `configs/<SwitchName>_show-run-output.txt` (this is
     the switch's own confirmation of what's actually configured, distinct
     from the config *script* you pasted in — keep both).
   - Take a screenshot of the full topology view and the PC1→PC2 (success)
     and PC2→PC1 (fail, ACL working) ping results, save under
     `packet_tracer/screenshots/`.

Once that's done, this folder contains genuine, checkable evidence: the
design, the exact commands used, the switches' own confirmation of their
running config, and proof the VLAN segmentation actually functions —
not just a claim that it does.
