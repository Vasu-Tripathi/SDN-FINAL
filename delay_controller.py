"""
Network Delay Measurement Tool - POX Controller
================================================
Handles packet_in events, installs flow rules, and logs
ICMP (ping) traffic for latency measurement and analysis.

Run with:
  ./pox.py log.level --DEBUG delay_controller
"""

from pox.core import core
from pox.lib.util import dpid_to_str
from pox.lib.revent import EventMixin
import pox.openflow.libopenflow_01 as of
from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.ipv4 import ipv4
from pox.lib.packet.icmp import icmp
import time

log = core.getLogger()

# ------------------------------------------------------------------
# Per-switch learning + flow-rule installer
# ------------------------------------------------------------------
class DelaySwitch(object):
    """
    One instance per connected switch.
    - Learns MAC→port mappings
    - Installs unicast flow rules (priority 10, idle_timeout 30s)
    - Logs every ICMP packet it sees for RTT analysis
    """

    def __init__(self, connection):
        self.connection = connection
        self.mac_to_port = {}          # {EthAddr: port_number}
        self.icmp_log = []             # [(timestamp, src_ip, dst_ip, direction)]

        connection.addListeners(self)
        log.info("Switch %s connected", dpid_to_str(connection.dpid))

    # ---- helpers ------------------------------------------------

    def _install_flow(self, match, out_port, priority=10, idle=30):
        """Install a match→action flow rule on the switch."""
        msg = of.ofp_flow_mod()
        msg.match = match
        msg.priority = priority
        msg.idle_timeout = idle
        msg.hard_timeout = 0
        msg.actions.append(of.ofp_action_output(port=out_port))
        self.connection.send(msg)

    def _flood(self, packet_in_event):
        """Flood a packet out all ports except the ingress port."""
        msg = of.ofp_packet_out()
        msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
        msg.data = packet_in_event.ofp
        msg.in_port = packet_in_event.port
        self.connection.send(msg)

    def _log_icmp(self, ip_pkt, direction):
        """Record ICMP event for delay analysis."""
        ts = time.time()
        entry = {
            "time": ts,
            "src":  str(ip_pkt.srcip),
            "dst":  str(ip_pkt.dstip),
            "dir":  direction,
        }
        self.icmp_log.append(entry)
        log.info("[ICMP] %s → %s  [%s]  t=%.4f", entry["src"], entry["dst"],
                 direction, ts)

    # ---- OpenFlow event -----------------------------------------

    def _handle_PacketIn(self, event):
        packet   = event.parsed
        in_port  = event.port

        if not packet.parsed:
            log.warning("Ignoring incomplete packet")
            return

        # --- Learn MAC → port ---
        self.mac_to_port[packet.src] = in_port

        # --- ICMP inspection for delay logging ---
        ip_pkt = packet.find('ipv4')
        if ip_pkt:
            ic_pkt = ip_pkt.find('icmp')
            if ic_pkt:
                direction = "REQUEST" if ic_pkt.type == icmp.TYPE_ECHO_REQUEST else "REPLY"
                self._log_icmp(ip_pkt, direction)

        # --- Forwarding decision ---
        dst_mac = packet.dst

        if dst_mac in self.mac_to_port:
            out_port = self.mac_to_port[dst_mac]

            # Build a match for this exact src/dst MAC pair
            match = of.ofp_match.from_packet(packet, in_port)
            self._install_flow(match, out_port)
            log.debug("Installed flow: %s → port %s", dst_mac, out_port)

            # Send this buffered packet out immediately
            msg = of.ofp_packet_out()
            msg.data    = event.ofp
            msg.in_port = in_port
            msg.actions.append(of.ofp_action_output(port=out_port))
            self.connection.send(msg)
        else:
            # Destination unknown — flood
            self._flood(event)

    def print_icmp_summary(self):
        """Print a summary of captured ICMP events (call from CLI if needed)."""
        if not self.icmp_log:
            log.info("No ICMP packets captured yet.")
            return
        log.info("=== ICMP Summary ===")
        for e in self.icmp_log:
            log.info("  [%s] %s → %s  at %.4f", e["dir"], e["src"], e["dst"], e["time"])


# ------------------------------------------------------------------
# POX component entry point
# ------------------------------------------------------------------
class DelayController(EventMixin):
    """
    Listens for new switch connections and attaches a DelaySwitch
    instance to each one.
    """

    def __init__(self):
        self.switches = {}   # dpid → DelaySwitch
        core.openflow.addListeners(self)
        log.info("DelayController started — waiting for switches...")

    def _handle_ConnectionUp(self, event):
        dpid = event.dpid
        log.info("New switch: %s", dpid_to_str(dpid))
        self.switches[dpid] = DelaySwitch(event.connection)

    def _handle_ConnectionDown(self, event):
        dpid = event.dpid
        if dpid in self.switches:
            log.info("Switch disconnected: %s", dpid_to_str(dpid))
            del self.switches[dpid]


def launch():
    """POX launch function — called by ./pox.py delay_controller"""
    core.registerNew(DelayController)
    log.info("Network Delay Measurement Controller loaded.")
