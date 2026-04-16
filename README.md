# 🌐 Network Delay Measurement Tool
**SDN-based Latency Analysis using Mininet + POX Controller**

> Measures and analyzes latency between hosts in a software-defined network using OpenFlow flow rules, ICMP ping, and iperf throughput testing.

---

## 📌 Problem Statement

Design and implement an SDN-based network simulation that:
- Measures **Round Trip Time (RTT)** between hosts using ICMP ping
- Records and compares **RTT values across different network paths**
- Analyzes **delay variations** between same-switch and cross-switch hosts
- Demonstrates **controller–switch interaction** via OpenFlow flow rules

---

## 🏗️ Topology Design

```
    h1 (10.0.0.1)
         |  5ms
        s1 ──────── 20ms ──────── s2
         |  5ms                    |  5ms
    h2 (10.0.0.2)            h3 (10.0.0.3)
```

| Component | Details |
|-----------|---------|
| Switches | 2x OVSSwitch (s1, s2) |
| Hosts | 3x hosts (h1, h2, h3) |
| Controller | POX (RemoteController, port 6633) |
| Link type | TCLink with artificial delay |
| h1–s1, h2–s1, h3–s2 | 5 ms delay each |
| s1–s2 inter-switch | 20 ms delay |

**Justification:** The asymmetric topology deliberately creates two measurable scenarios — low-latency same-switch communication (h1↔h2) and higher-latency cross-switch communication (h1↔h3) — to clearly demonstrate delay variation.

---

## ⚙️ Setup & Installation

### Prerequisites
```bash
sudo apt-get update
sudo apt-get install mininet iperf wireshark -y
```

### Install POX Controller
```bash
cd ~
git clone https://github.com/noxrepo/pox.git
cd pox
git checkout dart
```

### Copy Controller File
```bash
cp ~/SDN-FINAL-main/delay_controller.py ~/pox/ext/delay_controller.py
```

---

## ▶️ Execution Steps

### Step 1 — Start POX Controller (Terminal 1)
```bash
cd ~/pox
./pox.py log.level --DEBUG delay_controller
```
**Wait for:** `DelayController started — waiting for switches...`

### Step 2 — Start Mininet Topology (Terminal 2)
```bash
cd ~/SDN-FINAL-main
sudo python3 topology.py
```

### Step 3 — Manual Tests in Mininet CLI
```
mininet> h1 ping -c 5 h2
mininet> h1 ping -c 5 h3
mininet> sh ovs-ofctl dump-flows s1
mininet> sh ovs-ofctl dump-flows s2
mininet> exit
```

### Step 4 — Analyze Results (Terminal 3)
```bash
cd ~/SDN-FINAL-main
python3 analyze.py
```

> **Note:** Run `sudo mn -c` before restarting to clear Mininet state.

---

## 🧠 SDN Logic & Flow Rule Implementation

The POX controller (`delay_controller.py`) handles all OpenFlow logic:

### packet_in Handler
- Learns MAC → port mappings dynamically
- Inspects every arriving packet
- Logs ICMP REQUEST and REPLY events with timestamps

### Flow Rule Design (match–action)
```
match:  in_port + src_MAC + dst_MAC (from packet)
action: output → learned destination port
priority: 10
idle_timeout: 30s
```

Flow rules are installed using `ofp_flow_mod` on the first packet for each src/dst pair. Subsequent packets follow the rule directly at the switch without hitting the controller.

### ICMP Logging
Every ICMP packet is logged with:
```
[ICMP] 10.0.0.1 → 10.0.0.3  [REQUEST]  t=1776314328.6113
[ICMP] 10.0.0.3 → 10.0.0.1  [REPLY]    t=1776314328.7958
```

---

## 📸 Proof of Execution

### Controller Output — Flow Installation + ICMP Logging
><img width="940" height="529" alt="image" src="https://github.com/user-attachments/assets/d5e66ec3-0855-4f22-93a4-ca587698bb4f" />


---

### Topology Startup
> <img width="940" height="529" alt="image" src="https://github.com/user-attachments/assets/0b481ebb-5578-4efa-bb89-ecf0c71a3e73" />


---

## 🧪 Test Scenarios

### Scenario 1 — Same-Switch (h1 ↔ h2) — Low Latency
h1 and h2 both connect to s1. Path: h1 → s1 → h2. Only two 5ms links involved.

**Expected RTT:** ~20 ms

> <img width="940" height="529" alt="image" src="https://github.com/user-attachments/assets/a6e44b50-234c-4165-84b0-197e654b4d3c" />


---

### Scenario 2 — Cross-Switch (h1 ↔ h3) — Higher Latency
h1 connects to s1, h3 connects to s2. Path: h1 → s1 → s2 → h3. Includes the 20ms inter-switch link.

**Expected RTT:** ~60–140 ms

> <img width="940" height="529" alt="image" src="https://github.com/user-attachments/assets/c232136e-4dcf-4558-9e34-a5429e0a10d7" />

---

### Manual CLI Verification
> <img width="940" height="529" alt="image" src="https://github.com/user-attachments/assets/1cd7713f-4f55-4777-960a-dc6253f6e5cf" />


---

## 📊 Performance Observation & Analysis

### iperf Throughput — h1 → h2 (same switch)
> <img width="940" height="529" alt="image" src="https://github.com/user-attachments/assets/5ef70738-1612-4800-997f-fca3e3611f04" />


**Observation:** Same-switch path achieves ~1.95 Gbits/sec vs only ~7.19 Mbits/sec for the cross-switch path — the 20ms inter-switch link heavily impacts TCP throughput due to larger RTT increasing congestion window growth time.

---

### RTT Statistics — analyze.py Output
> **→ Insert image10 here** *(analyze.py showing min/avg/max/jitter for both paths + comparison table)*

| Path | Avg RTT | Min RTT | Max RTT | Jitter |
|------|---------|---------|---------|--------|
| h1 ↔ h2 (same switch) | 49.84 ms | 24.06 ms | 84.61 ms | 18.24 ms |
| h1 ↔ h3 (cross-switch) | 144.00 ms | 84.88 ms | 343.38 ms | 74.22 ms |

**Key finding:** Cross-switch RTT is ~3x higher on average, with ~4x more jitter — confirming the 20ms inter-switch link as the dominant latency factor.

---

### RTT Over Time — Path Comparison Graph
> <img width="940" height="529" alt="image" src="https://github.com/user-attachments/assets/1622303b-56f7-4691-993c-b6730c62c456" />


---

## 🔁 Flow Tables

### Switch s1 Flow Table
> <img width="940" height="529" alt="image" src="https://github.com/user-attachments/assets/296de109-f935-4e49-a0d0-8ed6346681d8" />

### Switch s2 Flow Table
> <img width="940" height="529" alt="image" src="https://github.com/user-attachments/assets/66abb1a7-9f26-4cbc-ada0-f534e07aff93" />


**Observation:** Flow rules are installed with `idle_timeout=30`, `priority=65535`. Packet counts (`n_packets`) increase with each ping confirming rules are being matched correctly.

---

## 📁 File Structure

```
SDN-FINAL-main/
├── delay_controller.py   # POX controller — packet_in, flow rules, ICMP logger
├── topology.py           # Mininet topology + automated test runner
├── analyze.py            # RTT parser, stats, matplotlib comparison plot
└── README.md             # This file
```

---

## ✅ Validation

- **0% packet loss** across all ping tests (10/10 packets received)
- Flow rules verified via `ovs-ofctl dump-flows` on both switches
- RTT consistently higher on cross-switch path in every run
- iperf confirms throughput degrades with higher latency path
- Controller correctly logs ICMP REQUEST + REPLY pairs with timestamps

---

## 📚 References

- [Mininet Documentation](http://mininet.org/api/index.html)
- [POX Controller Wiki](https://noxrepo.github.io/pox-doc/html/)
- [OpenFlow 1.0 Specification](https://opennetworking.org/wp-content/uploads/2013/04/openflow-spec-v1.0.0.pdf)
- [iperf Documentation](https://iperf.fr/iperf-doc.php)
- [Open vSwitch ofctl Manual](https://www.man7.org/linux/man-pages/man8/ovs-ofctl.8.html)
