import datetime
import json
import os.path

import dpkt
from dpkt import utils
from dpkt.utils import inet_to_str, mac_to_str


def ip_protocol_prop(self, indent=1):
    try:
        self._create_public_fields()
    except Exception:
        return "No protocol"

    l_ = []

    def add_field(fn, fv):
        if fn == "sum":
            l_.append("%s=%s" % (fn, fv))
        else:
            l_.append("%s=%s," % (fn, fv))

    for field_name in self.__public_fields__:
        if isinstance(self, dpkt.tcp.TCP):
            tcp = self
            d = {
                dpkt.tcp.TH_FIN: "FIN",
                dpkt.tcp.TH_SYN: "SYN",
                dpkt.tcp.TH_RST: "RST",
                dpkt.tcp.TH_PUSH: "PUSH",
                dpkt.tcp.TH_ACK: "ACK",
                dpkt.tcp.TH_URG: "URG",
            }

            active_flags = filter(lambda t: t[0] & tcp.flags, d.items())
            flags_str = " + ".join(t[1] for t in active_flags)

            flag = f"({str(flags_str)})"
        if not (
            "src" == field_name
            or "dst" == field_name
            or "urp" == field_name
            or "group" == field_name
        ):
            if "sport" == field_name:
                add_field("Source port", getattr(self, field_name))
                continue
            if "dport" == field_name:
                add_field("Destination port", getattr(self, field_name))
                continue
            if "flags" == field_name:
                add_field(field_name, flag)
                continue
            if "pro" == field_name:
                add_field("Protocol type", getattr(self, field_name))
                continue
            if "hln" == field_name:
                add_field("Hardware size", getattr(self, field_name))
                continue
            if "hrd" == field_name:
                add_field("Hardware type", getattr(self, field_name))
                continue
            if "pln" == field_name:
                add_field("Protocol size", getattr(self, field_name))
                continue
            if "op" == field_name:
                add_field("Opcode", getattr(self, field_name))
                continue
            if "sha" == field_name:
                add_field("Sender MAC address", "SenderMac")
                continue
            if "spa" == field_name:
                add_field("Sender IP address", "SenderIP")
                continue
            if "tha" == field_name:
                add_field("Target MAC address", "TargerMac")
                continue
            if "tpa" == field_name:
                add_field("Target IP address", "TargetIP")
                continue
            if "v" == field_name:
                add_field("Version", getattr(self, field_name))
                continue
            if "hl" == field_name:
                add_field("Header length", getattr(self, field_name))
                continue
            if "tos" == field_name:
                add_field("Differentiated services field", getattr(self, field_name))
                continue
            if "len" == field_name:
                add_field("Total length", getattr(self, field_name))
                continue
            if "id" == field_name:
                add_field("Identification", getattr(self, field_name))
                continue
            if "p" == field_name:
                add_field("Protocol", getattr(self, field_name))
                continue
            if "ttl" == field_name:
                add_field("Time to live", getattr(self, field_name))
                continue
            if "offset" == field_name:
                add_field("Fragment offset", getattr(self, field_name))
                continue
            if "rf" == field_name:
                add_field("Reserved bit", getattr(self, field_name))
                continue
            if "df" == field_name:
                add_field("Do not fragment", getattr(self, field_name))
                continue
            if "mf" == field_name:
                add_field("More fragments", getattr(self, field_name))
                continue
            if "tos" == field_name:
                add_field("Differentiated services field", getattr(self, field_name))
                continue
            if "sum" == field_name:
                add_field("Checksum", getattr(self, field_name))
                continue
            if "type" == field_name:
                add_field("Type", getattr(self, field_name))
                continue
            if "code" == field_name:
                add_field("Code", getattr(self, field_name))
                continue
            else:
                add_field(field_name, getattr(self, field_name))

    ip_prot = " %s: " % self.__class__.__name__
    for ii in l_:
        ip_prot += " " * indent + "%s" % ii
    return ip_prot


def create_mimishark_json(pcap, to_json):
    json_file = []

    with open(to_json, "w") as file:
        for timestamp, buf in pcap:
            pcap_file = {}
            eth = dpkt.ethernet.Ethernet(buf)
            if isinstance(eth.data, dpkt.arp.ARP):
                arp_pkt = eth.data
                pcap_file["time"] = str(datetime.datetime.utcfromtimestamp(timestamp))
                pcap_file["source"] = str(utils.mac_to_str(arp_pkt.sha))
                pcap_file["destination"] = str(utils.mac_to_str(eth.dst))
                pcap_file["protocol"] = "ARP"
                pcap_file["length"] = len(mac_to_str(buf).split(":"))

                bytes_repr = " ".join(mac_to_str(buf).split(":"))
                ascii = ""
                for i in bytes_repr.split(" "):
                    a = bytes.fromhex(i)
                    b = str(a)[2 : len((str(a))) - 1]
                    if len(b) < 2:
                        ascii += b
                    else:
                        ascii += "."

                pcap_file["ascii"] = ascii.replace('"', "doublePrime").replace(
                    "'", "singlePrime"
                )
                pcap_file["bytes"] = bytes_repr

                pcap_file["decode_eth"] = (
                    f" Ethernet Frame:  Destination: {mac_to_str(eth.dst)}  Sourse:"
                    f" {mac_to_str(eth.src)}  Type: ARP"
                    f" (0x{bytes_repr[36:41].replace(' ','')})"
                )
                pcap_file["decode_arp"] = (
                    ip_protocol_prop(arp_pkt)
                    .replace("SenderMac", str(utils.mac_to_str(arp_pkt.sha)))
                    .replace("SenderIP", str(utils.inet_to_str(arp_pkt.spa)))
                    .replace("TargerMac", str(utils.mac_to_str(eth.dst)))
                    .replace("TargetIP", str(utils.inet_to_str(arp_pkt.tpa)))
                )
                # .replace('"','doublePrime').replace("'",'singlePrime').replace('\\','doubleslash')
                json_file.append(pcap_file)
            if isinstance(eth.data, dpkt.ip.IP):
                pcap_file["time"] = str(datetime.datetime.utcfromtimestamp(timestamp))

                ip = eth.data
                pcap_file["source"] = inet_to_str(ip.src)
                pcap_file["destination"] = inet_to_str(ip.dst)
                pcap_file["protocol"] = ip.get_proto(ip.p).__name__
                pcap_file["length"] = len(mac_to_str(buf).split(":"))

                bytes_repr = " ".join(mac_to_str(buf).split(":"))
                ascii = ""
                for i in bytes_repr.split(" "):
                    a = bytes.fromhex(i)
                    b = str(a)[2 : len((str(a))) - 1]
                    if len(b) < 2:
                        ascii += b
                    else:
                        ascii += "."
                pcap_file["ascii"] = ascii.replace('"', "doublePrime").replace(
                    "'", "singlePrime"
                )
                pcap_file["bytes"] = bytes_repr
                pcap_file["decode_eth"] = (
                    f" Ethernet Frame:  Destination: {mac_to_str(eth.dst)}  Sourse:"
                    f" {mac_to_str(eth.src)}  Type:"
                    f" IPv{ip.v} (0x{bytes_repr[36:41].replace(' ','')})"
                )
                pcap_file["decode_ip"] = (
                    ip_protocol_prop(ip)
                    + " Source Address: "
                    + inet_to_str(ip.src)
                    + ", Destination Address: "
                    + inet_to_str(ip.dst)
                )
                pcap_file[f"decode_{ip.data.__class__.__name__}"] = ip_protocol_prop(
                    ip.data
                )
                json_file.append(pcap_file)

        print(json.dumps(json_file), file=file)


def from_pcap_to_json(from_pcap, to_json):
    # Do we already have a JSON file?
    if os.path.isfile(to_json):
        return to_json

    # No ?
    # Is pcap file exists?
    if not os.path.isfile(from_pcap):
        return False

    with open(from_pcap, "rb") as f:
        pcap = dpkt.pcap.Reader(f)
        create_mimishark_json(pcap, to_json)
