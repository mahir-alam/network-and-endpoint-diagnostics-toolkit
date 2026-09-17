# Packet Tracer Topology — Design Reference

This is a small, single-building network design: one Layer 3 distribution
switch handling inter-VLAN routing, two Layer 2 access switches feeding
end devices, and two VLANs (Staff / Guest) plus a dedicated management
VLAN — a realistic, small-office pattern, not an arbitrary lab toy.

## Diagram

```
                         ┌─────────────────────┐
                         │     DistSwitch1      │
                         │  (Catalyst 3560, L3) │
                         │                      │
                         │  VLAN10 SVI .10.1    │
                         │  VLAN20 SVI .20.1    │
                         │  VLAN99 SVI .99.1    │
                         └──────────┬───────────┘
                        Trunk (10,20,99)   Trunk (10,20,99)
                    ┌────────────────┴───┐   ┌──┴──────────────────┐
                    │                    │   │                     │
            ┌───────┴───────┐    ┌───────┴───┴───┐
            │ AccessSwitch1 │    │ AccessSwitch2 │
            │  (Catalyst    │    │  (Catalyst    │
            │   2960)       │    │   2960)       │
            │ Mgmt .99.2    │    │ Mgmt .99.3    │
            └───┬───────┬───┘    └───┬───────┬───┘
                │       │            │       │
           VLAN10     VLAN20    VLAN10     VLAN20
                │       │            │       │
             ┌──┴──┐ ┌──┴──┐      ┌──┴──┐ ┌──┴──┐
             │ PC1 │ │ PC2 │      │ PC3 │ │ PC4 │
             │.10.10│ │.20.10│    │.10.11│ │.20.11│
             └─────┘ └─────┘      └─────┘ └─────┘
```

## Device roles

| Device         | Role                                    | Platform (in Packet Tracer) |
|----------------|------------------------------------------|------------------------------|
| DistSwitch1    | Inter-VLAN routing (SVIs), trunk aggregation | Cisco Catalyst 3560 (multilayer) |
| AccessSwitch1  | Access-layer switching, VLAN 10 + 20 ports | Cisco Catalyst 2960 |
| AccessSwitch2  | Access-layer switching, VLAN 10 + 20 ports | Cisco Catalyst 2960 |
| PC1, PC3       | Staff workstations                       | Generic PC (VLAN 10) |
| PC2, PC4       | Guest workstations                       | Generic PC (VLAN 20) |

## IP addressing scheme

| VLAN | Name  | Subnet             | Gateway (DistSwitch1 SVI) | Notes |
|------|-------|--------------------|-----------------------------|-------|
| 10   | STAFF | 192.168.10.0/24     | 192.168.10.1               | Staff workstations |
| 20   | GUEST | 192.168.20.0/24     | 192.168.20.1               | Guest workstations, restricted from reaching VLAN 10 by ACL |
| 99   | MGMT  | 192.168.99.0/24     | 192.168.99.1               | Switch management SVIs only |

| Device            | Interface       | IP Address     |
|-------------------|-----------------|----------------|
| DistSwitch1       | Vlan10 (SVI)    | 192.168.10.1   |
| DistSwitch1       | Vlan20 (SVI)    | 192.168.20.1   |
| DistSwitch1       | Vlan99 (SVI)    | 192.168.99.1   |
| AccessSwitch1     | Vlan99 (SVI)    | 192.168.99.2   |
| AccessSwitch2     | Vlan99 (SVI)    | 192.168.99.3   |
| PC1               | NIC             | 192.168.10.10  |
| PC2               | NIC             | 192.168.20.10  |
| PC3               | NIC             | 192.168.10.11  |
| PC4               | NIC             | 192.168.20.11  |

These addresses are deliberately reused as `IsLocalHost=False` rows in
`inventory/device_inventory.xlsx` (`PT-DistSwitch1-Mgmt`, `PT-PC1-VLAN10`,
`PT-PC2-VLAN20`) so the Layer 1 Python monitor's device list visibly
mirrors this topology's addressing — see the "Why Packet Tracer devices
show as DOWN" note in the top-level README for why they don't actually
resolve as reachable when the toolkit runs outside Packet Tracer.

## Security/segmentation feature demonstrated

`DistSwitch1` applies a standard ACL (`GUEST-RESTRICT`) inbound on the
VLAN 20 SVI that denies traffic destined for the 192.168.10.0/24 (Staff)
subnet while permitting everything else — a real, minimal demonstration
of VLANs being used for actual traffic segmentation, not just broadcast
domain separation on paper.
