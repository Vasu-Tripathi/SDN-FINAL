#!/usr/bin/env python3
"""
Network Delay Measurement Tool - RTT Analysis
==============================================
Parses ping log files produced by topology.py and prints
summary statistics (min / avg / max / jitter).
Optionally plots RTT over time if matplotlib is available.

Usage:
  python3 analyze.py                          # uses /tmp/ping_*.txt
  python3 analyze.py path/to/ping_log.txt    # specific file
"""

import re
import sys
import os
import glob

# ── Parser ────────────────────────────────────────────────────────

def parse_ping_file(filepath):
    """
    Extract per-ping RTT values (ms) from a ping output file.
    Returns list of floats.
    """
    rtt_values = []
    rtt_pattern = re.compile(r'time[=<](\d+\.?\d*)\s*ms')

    with open(filepath) as f:
        for line in f:
            m = rtt_pattern.search(line)
            if m:
                rtt_values.append(float(m.group(1)))
    return rtt_values


def parse_summary_line(filepath):
    """Extract min/avg/max/mdev from ping summary line."""
    summary = {}
    pattern = re.compile(
        r'(\d+\.?\d+)/(\d+\.?\d+)/(\d+\.?\d+)/(\d+\.?\d+)'
    )
    with open(filepath) as f:
        for line in f:
            m = pattern.search(line)
            if m:
                summary = {
                    'min':   float(m.group(1)),
                    'avg':   float(m.group(2)),
                    'max':   float(m.group(3)),
                    'mdev':  float(m.group(4)),
                }
    return summary


# ── Reporter ──────────────────────────────────────────────────────

def print_report(filepath):
    name = os.path.basename(filepath).replace('.txt', '')
    rtts = parse_ping_file(filepath)
    summary = parse_summary_line(filepath)

    print(f"\n{'='*50}")
    print(f"  {name}")
    print(f"{'='*50}")

    if not rtts:
        print("  No RTT data found.")
        return

    if summary:
        print(f"  Packets captured : {len(rtts)}")
        print(f"  Min RTT          : {summary['min']:.3f} ms")
        print(f"  Avg RTT          : {summary['avg']:.3f} ms")
        print(f"  Max RTT          : {summary['max']:.3f} ms")
        print(f"  Jitter (mdev)    : {summary['mdev']:.3f} ms")
    else:
        # Compute manually if ping summary line not found
        mn  = min(rtts)
        mx  = max(rtts)
        avg = sum(rtts) / len(rtts)
        variance = sum((r - avg)**2 for r in rtts) / len(rtts)
        jitter = variance ** 0.5

        print(f"  Packets captured : {len(rtts)}")
        print(f"  Min RTT          : {mn:.3f} ms")
        print(f"  Avg RTT          : {avg:.3f} ms")
        print(f"  Max RTT          : {mx:.3f} ms")
        print(f"  Jitter (stddev)  : {jitter:.3f} ms")


def compare_paths(files):
    """Print a comparison table for multiple ping log files."""
    rows = []
    for fp in files:
        rtts = parse_ping_file(fp)
        summary = parse_summary_line(fp)
        label = os.path.basename(fp).replace('ping_', '').replace('.txt', '')
        if summary:
            rows.append((label, summary['avg'], summary['min'],
                         summary['max'], summary['mdev']))
        elif rtts:
            avg = sum(rtts) / len(rtts)
            rows.append((label, avg, min(rtts), max(rtts), 0.0))

    if not rows:
        return

    print(f"\n{'='*65}")
    print(f"  PATH COMPARISON")
    print(f"{'='*65}")
    print(f"  {'Path':<25} {'Avg(ms)':>10} {'Min(ms)':>10} {'Max(ms)':>10} {'Jitter':>8}")
    print(f"  {'-'*60}")
    for r in rows:
        print(f"  {r[0]:<25} {r[1]:>10.2f} {r[2]:>10.2f} {r[3]:>10.2f} {r[4]:>8.2f}")
    print()


def try_plot(files):
    """Optional matplotlib plot — skipped gracefully if not available."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(matplotlib not installed — skipping plot)")
        return

    plt.figure(figsize=(10, 5))
    for fp in files:
        rtts = parse_ping_file(fp)
        if rtts:
            label = os.path.basename(fp).replace('ping_', '').replace('.txt', '')
            plt.plot(rtts, marker='o', label=label, linewidth=1.5)

    plt.title("RTT over Time — Path Comparison")
    plt.xlabel("Ping sequence number")
    plt.ylabel("RTT (ms)")
    plt.legend()
    plt.grid(True, alpha=0.4)
    plt.tight_layout()
    out = "/tmp/rtt_plot.png"
    plt.savefig(out, dpi=150)
    print(f"\n  RTT plot saved → {out}")
    plt.show()


# ── Main ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = sorted(glob.glob('/tmp/ping_*.txt'))

    if not files:
        print("No ping log files found. Run topology.py first.")
        sys.exit(1)

    for fp in files:
        if os.path.exists(fp):
            print_report(fp)
        else:
            print(f"File not found: {fp}")

    compare_paths(files)
    try_plot(files)
