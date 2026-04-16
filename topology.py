#!/usr/bin/env python3
"""
Network Delay Measurement Tool - Mininet Topology
===================================================
Topology:
          h1
          |
         s1 ---- s2
          |       |
         h2      h3

Links are given artificial delays so RTT differences are visible:
  h1-s1 : 5 ms
  h2-s1 : 5 ms
  s1-s2 : 20 ms   ← the "slow" inter-switch link
  h3-s2 : 5 ms

Expected approximate RTTs:
  h1 ↔ h2 :  ~20 ms   (same switch)
  h1 ↔ h3 :  ~60 ms   (cross-switch, through 20 ms link)
  h2 ↔ h3 :  ~60 ms

Run:
  sudo python3 topology.py
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info
import time
import subprocess
import os

# ── Topology ──────────────────────────────────────────────────────

def build_network():
    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        link=TCLink,          # enables delay/bw parameters
        autoSetMacs=True,
    )

    info("*** Adding controller (POX at 127.0.0.1:6633)\n")
    c0 = net.addController('c0',
                            controller=RemoteController,
                            ip='127.0.0.1',
                            port=6633)

    info("*** Adding switches\n")
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')

    info("*** Adding hosts\n")
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')

    info("*** Adding links with delay parameters\n")
    net.addLink(h1, s1, delay='5ms')
    net.addLink(h2, s1, delay='5ms')
    net.addLink(s1, s2, delay='20ms')   # slow inter-switch link
    net.addLink(h3, s2, delay='5ms')

    return net, c0, [s1, s2], [h1, h2, h3]


# ── Test scenarios ────────────────────────────────────────────────

def run_ping_test(net, src_name, dst_name, count=10):
    """Ping from src to dst, capture RTT stats, save to log."""
    src = net.get(src_name)
    dst = net.get(dst_name)
    dst_ip = dst.IP()

    info(f"\n{'='*55}\n")
    info(f"  Scenario: {src_name} → {dst_name}  (target IP {dst_ip})\n")
    info(f"{'='*55}\n")

    result = src.cmd(f"ping -c {count} -i 0.5 {dst_ip}")
    info(result)

    # Write raw output to file
    log_file = f"/tmp/ping_{src_name}_{dst_name}.txt"
    with open(log_file, 'w') as f:
        f.write(f"Ping: {src_name} ({src.IP()}) → {dst_name} ({dst_ip})\n")
        f.write(result)
    info(f"  [Saved to {log_file}]\n")
    return result


def run_iperf_test(net, src_name, dst_name, duration=5):
    """TCP throughput test with iperf."""
    src = net.get(src_name)
    dst = net.get(dst_name)
    dst_ip = dst.IP()

    info(f"\n{'='*55}\n")
    info(f"  iperf: {src_name} → {dst_name}\n")
    info(f"{'='*55}\n")

    # Start server on dst
    dst.cmd('iperf -s &')
    time.sleep(1)

    result = src.cmd(f"iperf -c {dst_ip} -t {duration}")
    info(result)

    dst.cmd('kill %iperf 2>/dev/null')

    log_file = f"/tmp/iperf_{src_name}_{dst_name}.txt"
    with open(log_file, 'w') as f:
        f.write(f"iperf: {src_name} → {dst_name}\n")
        f.write(result)
    info(f"  [Saved to {log_file}]\n")
    return result


def run_all_tests(net):
    """
    Scenario 1 – Same-switch hosts (h1 ↔ h2): low latency
    Scenario 2 – Cross-switch hosts (h1 ↔ h3): higher latency (20ms inter-link)
    """
    info("\n\n*** Warming up flows (initial ping) ***\n")
    net.get('h1').cmd('ping -c 2 10.0.0.2')
    net.get('h1').cmd('ping -c 2 10.0.0.3')
    time.sleep(2)

    info("\n\n*** SCENARIO 1: Same-switch (h1 ↔ h2 — low latency) ***\n")
    run_ping_test(net, 'h1', 'h2', count=10)

    info("\n\n*** SCENARIO 2: Cross-switch (h1 ↔ h3 — higher latency) ***\n")
    run_ping_test(net, 'h1', 'h3', count=10)

    info("\n\n*** iperf throughput: h1 → h2 ***\n")
    run_iperf_test(net, 'h1', 'h2')

    info("\n\n*** iperf throughput: h1 → h3 ***\n")
    run_iperf_test(net, 'h1', 'h3')

    info("\n\n*** Flow table dump (s1) ***\n")
    result = subprocess.run(['ovs-ofctl', 'dump-flows', 's1'],
                            capture_output=True, text=True)
    info(result.stdout)
    with open('/tmp/flow_table_s1.txt', 'w') as f:
        f.write(result.stdout)

    info("\n*** Flow table dump (s2) ***\n")
    result = subprocess.run(['ovs-ofctl', 'dump-flows', 's2'],
                            capture_output=True, text=True)
    info(result.stdout)
    with open('/tmp/flow_table_s2.txt', 'w') as f:
        f.write(result.stdout)

    info("\n\n*** All tests complete. Results saved in /tmp/ ***\n")
    info("  ping logs   : /tmp/ping_*.txt\n")
    info("  iperf logs  : /tmp/iperf_*.txt\n")
    info("  flow tables : /tmp/flow_table_s*.txt\n")


# ── Main ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    setLogLevel('info')

    net, c0, switches, hosts = build_network()

    info("\n*** Starting network\n")
    net.start()

    info("\n*** Waiting 3 s for POX controller to install rules...\n")
    time.sleep(3)

    # Run automated test scenarios
    run_all_tests(net)

    info("\n*** Dropping into Mininet CLI (type 'exit' when done)\n")
    CLI(net)

    net.stop()
    info("Network stopped.\n")
