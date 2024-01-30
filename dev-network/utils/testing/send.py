from scapy.all import *
import argparse

# declare hosts
hosts = {
    "h1": {
        "src_mac": "08:00:00:10:00:10",
        "dst_mac": "08:00:00:00:01:00",
        "ipv4": "10.100.0.10",
        "ipv6": "2001:DB8:64::10",
    },
    "h2": {
        "src_mac": "08:00:00:20:10:20",
        "dst_mac": "08:00:00:00:04:00",
        "ipv4": "10.200.0.20",
        "ipv6": "2001:DB8:C8::20",
    },
    "h3": {
        "src_mac": "08:00:00:20:10:30",
        "dst_mac": "08:00:00:00:04:00",
        "ipv4": "10.201.0.30",
        "ipv6": "2001:DB8:C9::30",
    },
    "h4": {
        "src_mac": "08:00:00:25:50:40",
        "dst_mac": "08:00:00:00:04:00",
        "ipv4": "10.255.0.40",
        "ipv6": "2001:DB8:FF::40",
    },
}


def set_ethernet_address(src, dst, packet):
    packet.getlayer("Ethernet").src = hosts[src]["src_mac"]
    packet.getlayer("Ethernet").dst = hosts[src]["dst_mac"]


def set_ipv4_address(src, dst, packet):
    packet.getlayer("IP").src = hosts[src]["ipv4"]
    packet.getlayer("IP").dst = hosts[dst]["ipv4"]


def set_ipv6_address(src, dst, packet):
    packet.getlayer("IPv6").src = hosts[src]["ipv6"]
    packet.getlayer("IPv6").dst = hosts[dst]["ipv6"]


# send imported IPv4 packets from src to dst
def send_ipv4_packets(src, dst, count):
    ipv4_packets = rdpcap("./dev-network/utils/captures/quic_ipv4.pcapng")
    packet_counter = 0
    while packet_counter < count:
        for packet in ipv4_packets:
            if packet_counter >= count:
                break
            set_ethernet_address(src, dst, packet)
            set_ipv4_address(src, dst, packet)
            sendp(packet)
            packet_counter += 1


# send imported IPv6 packets from src to dst
def send_ipv6_packets(src, dst, count):
    ipv6_packets = rdpcap("./dev-network/utils/captures/quic_ipv6.pcapng")
    packet_counter = 0
    while packet_counter < count:
        for packet in ipv6_packets:
            if packet_counter >= count:
                break
            set_ethernet_address(src, dst, packet)
            set_ipv6_address(src, dst, packet)
            sendp(packet)
            packet_counter += 1


# initialize argparse
parser = argparse.ArgumentParser(description="Network Traffic Simulator")
parser.add_argument("--ipv4", help="Send only IPv4 traffic", action="store_true")
parser.add_argument("--ipv6", help="Send only IPv6 traffic", action="store_true")
parser.add_argument("--src", help="The source of the traffic", default="h1")
parser.add_argument("--dst", help="The destion of the traffic", default="h3")
parser.add_argument("--count", help="Number of packets to be sent", default=10)
args = parser.parse_args()


# decide which functions to call
if args.ipv4:
    print(f"Sending {args.count} IPv4 packets from {args.src} to {args.dst}")
    print(f'{hosts[args.src]["ipv4"]} --> {hosts[args.dst]["ipv4"]}')
    send_ipv4_packets(args.src, args.dst, int(args.count))
elif args.ipv6:
    print(f"Sending {args.count} IPv6 packets from {args.src} to {args.dst}")
    print(f'{hosts[args.src]["ipv6"]} --> {hosts[args.dst]["ipv6"]}')
    send_ipv6_packets(args.src, args.dst, int(args.count))
else:
    print(f"Sending {args.count} IPv4 and IPv6 packets from {args.src} to {args.dst}")
    print(f'{hosts[args.src]["ipv4"]} --> {hosts[args.dst]["ipv4"]}')
    print(f'{hosts[args.src]["ipv6"]} --> {hosts[args.dst]["ipv6"]}')
    send_ipv4_packets(args.src, args.dst, int(args.count))
    send_ipv6_packets(args.src, args.dst, int(args.count))
