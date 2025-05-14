import datetime
import json
import os.path

import dpkt
from dpkt import utils
from dpkt.utils import inet_to_str, mac_to_str


def create_mimishark_json(pcap, to_json):
    json_file = []
    start_timestamp = 0

    with open(to_json, "w") as file:
        for timestamp, buf in pcap:
            pcap_file = {}
            eth = dpkt.ethernet.Ethernet(buf)

            if not start_timestamp:
                start_timestamp = datetime.datetime.fromtimestamp(timestamp)
                pcap_file["time"] = "00:00.000000"
            else:
                dt = datetime.datetime.fromtimestamp(timestamp) - start_timestamp
                pcap_file["time"] = ":".join(str(dt).split(":")[1:])

            if isinstance(eth.data, dpkt.arp.ARP):
                arp_pkt = eth.data
                pcap_file["source"] = str(utils.mac_to_str(arp_pkt.sha))
                pcap_file["destination"] = str(utils.mac_to_str(eth.dst))
                pcap_file["protocol"] = "ARP"
                pcap_file["length"] = str(len(mac_to_str(buf).split(":")))

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

                # .replace('"','doublePrime').replace("'",'singlePrime').replace('\\','doubleslash')
                json_file.append(pcap_file)

            if isinstance(eth.data, dpkt.llc.LLC):
                llc = eth.data

                pcap_file["source"] = str(utils.mac_to_str(eth.src))
                pcap_file["destination"] = str(utils.mac_to_str(eth.dst))
                pcap_file["length"] = len(mac_to_str(buf).split(":"))

                if llc.dsap == 0x42:
                    data = bytes(llc.data)
                    version = data[2]
                    if version == 0x02:
                        match llc.data.flags & 0x03:
                            case 0:
                                pcap_file["protocol"] = "RSTP (Unknown)"
                            case 1:
                                pcap_file["protocol"] = "RSTP (Alternate/Backup)"
                            case 2:
                                pcap_file["protocol"] = "RSTP (Root)"
                            case 3:
                                pcap_file["protocol"] = "RSTP (Designated)"
                            case _:
                                pcap_file["protocol"] = "RSTP (Reserved)"
                    else:
                        match llc.data.flags:
                            case 0:
                                pcap_file["protocol"] = "STP (Root)"
                            case 1:
                                pcap_file["protocol"] = "STP (TC + Root)"
                            case _:
                                pcap_file["protocol"] = "STP"

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
                    json_file.append(pcap_file)

            if isinstance(eth.data, dpkt.ip.IP):
                ip = eth.data
                pcap_file["source"] = inet_to_str(ip.src)
                pcap_file["destination"] = inet_to_str(ip.dst)
                pcap_file["protocol"] = ip.get_proto(ip.p).__name__
                pcap_file["length"] = str(len(mac_to_str(buf).split(":")))

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
