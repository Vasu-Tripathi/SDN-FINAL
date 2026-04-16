# Network Delay Measurement Tool
**SDN Mininet Project — POX Controller**

## Problem Statement
Measure and analyze latency between hosts in an SDN network. The controller observes ICMP (ping) traffic, installs OpenFlow flow rules, and enables RTT comparison across paths of different lengths.

---

## Topology
```
    h1 (10.0.0.1)
     |  5ms
    s1 ─────── 20ms ─────── s2
     |  5ms                  |  5ms
    h2 (10.0.0.2)         h3 (10.0.0.3)
```

| Path | Expected RTT |
|------|-------------|
| h1 ↔ h2 (same switch) | ~20 ms |
| h1 ↔ h3 (cross-switch) | ~60 ms |

---

## Prerequisites & Installation

### 1. Install Mininet
```bash
sudo apt-get update
sudo apt-get install mininet -y
```

### 2. Install POX Controller
```bash
cd ~
git clone https://github.com/noxrepo/pox.git
cd pox
git checkout dart    # stable branch
```

### 3. Install tools for testing
```bash
sudo apt-get install iperf wireshark -y
```

### 4. Copy controller file
```bash
cp /path/to/delay_controller.py ~/pox/ext/delay_controller.py
```

---

## Running the Project

### Step 1 — Start the POX controller (Terminal 1)
```bash
cd ~/pox
./pox.py log.level --DEBUG delay_controller
```
You should see: `DelayController started — waiting for switches...`

### Step 2 — Start the Mininet topology (Terminal 2)
```bash
sudo python3 topology.py
```
This will:
- Build the two-switch topology with artificial link delays
- Run **Scenario 1** (h1 ↔ h2, same switch — low latency)
- Run **Scenario 2** (h1 ↔ h3, cross-switch — higher latency)
- Run iperf throughput tests
- Dump flow tables from both switches
- Drop into the Mininet CLI

### Step 3 — Manual tests inside Mininet CLI (optional)
```
mininet> h1 ping -c 5 h2
mininet> h1 ping -c 5 h3
mininet> h1 iperf h2
mininet> sh ovs-ofctl dump-flows s1
mininet> exit
```

### Step 4 — Analyze results (Terminal 3)
```bash
python3 analyze.py
```

---

## Test Scenarios

### Scenario 1 — Same-switch (low latency)
h1 and h2 connect to the same switch (s1). With 5 ms link delay on each side, RTT ≈ 20 ms.

### Scenario 2 — Cross-switch (higher latency)
h1 → s1 → s2 → h3 adds the 20 ms inter-switch link. RTT ≈ 60 ms.

---

## Expected Output

### Ping results
```
--- 10.0.0.2 ping statistics ---
10 packets transmitted, 10 received, 0% packet loss
rtt min/avg/max/mdev = 18.3/20.1/22.4/1.2 ms

--- 10.0.0.3 ping statistics ---
10 packets transmitted, 10 received, 0% packet loss
rtt min/avg/max/mdev = 58.1/60.4/63.2/1.8 ms
```

### Flow table (s1)
```
cookie=0x0, duration=Xs, table=0, n_packets=N, priority=10,
  ip,in_port=1,dl_src=00:00:00:00:00:01,dl_dst=00:00:00:00:00:02
  actions=output:2
```

### Analysis comparison table
```
PATH                      Avg(ms)    Min(ms)    Max(ms)   Jitter
------------------------------------------------------------
h1_h2                      20.10      18.30      22.40     1.20
h1_h3                      60.40      58.10      63.20     1.80
```

---

## Files
| File | Description |
|------|-------------|
| `delay_controller.py` | POX controller — packet_in handler, flow rule installer, ICMP logger |
| `topology.py` | Mininet topology + automated test runner |
| `analyze.py` | RTT parser, statistics reporter, optional matplotlib plot |
| `README.md` | This file |

---

## References
- [Mininet Documentation](http://mininet.org/api/index.html)
- [POX Wiki](https://noxrepo.github.io/pox-doc/html/)
- [OpenFlow 1.0 Spec](https://opennetworking.org/wp-content/uploads/2013/04/openflow-spec-v1.0.0.pdf)
- [iperf Manual](https://iperf.fr/iperf-doc.php)
