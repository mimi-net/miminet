import time
import json
import os.path
import string
import random
import signal
import os
import re
import shutil

from ipmininet.iptopo import IPTopo
from ipmininet.ipnet import IPNet
from mininet.log import setLogLevel
from ipmininet.ipswitch import IPSwitch
from ipmininet.router.config import RouterConfig
from pkt_parser import create_pkt_animation, is_ipv4_address

jnet = ''
time_to_wait_before_emulation = 2


class MyTopology(IPTopo):

    def __init__(self, *args, **kwargs):
        self.switch_count = 0
        super().__init__(*args, **kwargs)

    def build(self, *args, **kwargs):

        nodes = {}
        ifaces = []
        ifs = []

        self.link_pair = []
        global time_to_wait_before_emulation
        time_to_wait_before_emulation = 2

        # Add hosts and switches
        for d in jnet.get('nodes', []):
            node_type = d.get('config', []).get('type', [])
            node_id = d.get('data', []).get('id', [])

            if (node_type == 'l2_switch'):

                stp = d.get('config', []).get('stp', 0)
                nodes[node_id] = self.addSwitch(node_id, cls=IPSwitch, stp=stp)

                if stp:
                    time_to_wait_before_emulation = 33

            elif (node_type == 'host' or node_type == 'server'):

                default_gw = d.get('config', []).get('default_gw', [])

                if default_gw:
                    nodes[node_id] = self.addHost(node_id, defaultRoute='via ' + str(default_gw))
                else:
                    nodes[node_id] = self.addHost(node_id, defaultRoute='')

            elif (node_type == 'l1_hub'):
                nodes[node_id] = self.addSwitch(node_id, cls=IPSwitch, stp=False, hub=True)
            elif (node_type == 'router'):

                default_gw = d.get('config', []).get('default_gw', [])

                if default_gw:
                    nodes[node_id] = self.addRouter(node_id, use_v6=False, routerDefaultRoute='via ' + str(default_gw),
                                                    config=RouterConfig)
                else:
                    nodes[node_id] = self.addRouter(node_id, use_v6=False, config=RouterConfig)

        # Add links
        for e in jnet.get('edges', []):
            e_id = e.get('data', []).get('id', [])
            e_source = e.get('data', []).get('source')
            e_target = e.get('data', []).get('target')

            h_source = nodes[e_source]
            h_target = nodes[e_target]

            if not h_source or not h_target:
                continue

            ifname_source = ''
            ifname_target = ''

            ifname_source_ip = ''
            ifname_source_netmask = ''

            ifname_target_ip = ''
            ifname_target_netmask = ''

            for h in jnet.get('nodes', []):
                node_id = h.get('data', []).get('id', [])

                if node_id == e_source:
                    # Find source, iterate over interfaces to findout ifname
                    for i in h.get('interface', []):
                        if e_id == i.get('connect', []):
                            ifname_source = i.get('name', '')
                            ifname_source_ip = i.get('ip', '')
                            ifname_source_netmask = i.get('netmask', 0)

                            if not ifname_source_netmask:
                                ifname_source_netmask = 0

                            ifname_source_netmask = int(ifname_source_netmask)

                if node_id == e_target:
                    for i in h.get('interface', []):
                        if e_id == i.get('connect', []):
                            ifname_target = i.get('name', '')
                            ifname_target_ip = i.get('ip', '')
                            ifname_target_netmask = i.get('netmask', 0)

                            if not ifname_target_netmask:
                                ifname_target_netmask = 0

                            ifname_target_netmask = int(ifname_target_netmask)

            if not ifname_source or not ifname_target:
                continue

            self.link_pair.append((ifname_source, ifname_target, e_id, e_source, e_target))
            l1, l2 = self.addLink(h_source, h_target, intfName1=ifname_source, intfName2=ifname_target, delay='15ms')

            if is_ipv4_address(ifname_source_ip) and ifname_source_netmask > 0 and ifname_source_netmask <= 32:
                l1[h_source].addParams(ip=(str(ifname_source_ip) + '/' + str(ifname_source_netmask)))

            if is_ipv4_address(ifname_target_ip) and ifname_target_netmask > 0 and ifname_target_netmask <= 32:
                l2[h_target].addParams(ip=(str(ifname_target_ip) + '/' + str(ifname_target_netmask)))

            ifaces.append(l1[h_source])
            ifaces.append(l2[h_target])

            ifs.append(ifname_source)
            ifs.append(ifname_target)

        if ifaces:
            print('-----------------------------')
            print(ifaces)
            print(*ifaces)
            print(ifs)
            self.addNetworkCapture(nodes=[],
                                   interfaces=[*ifaces],
                                   base_filename="capture",
                                   extra_arguments="-v -c 100 -Qout not igmp")

        super().build(*args, **kwargs)

    def addLink(self, h_source, h_target, intfName1, intfName2, delay='2ms', max_queue_size=None):
        self.switch_count += 1
        s = "mimiswsw%d" % self.switch_count
        self.addSwitch(s, cls=IPSwitch, stp=False, hub=True)

        opts1 = dict()
        opts2 = dict()

        # switch -> node1
        opts1["params2"] = {"delay": delay,
                            "max_queue_size": max_queue_size}
        # switch -> node2
        opts2["params1"] = {"delay": delay,
                            "max_queue_size": max_queue_size}

        return super().addLink(h_source, s, intfName1=intfName1, **opts1), \
            super().addLink(s, h_target, intfName2=intfName2, **opts2)


def packet_uuid(size=8, chars=string.ascii_uppercase + string.digits):
    uid = ''.join(random.choice(chars) for _ in range(size))
    return 'pkt_' + uid


def do_job(job, job_host):
    job_id = int(job.get('job_id'))
    print("Do job: " + str(job))

    # Ping
    if job_id == 1:
        arg1 = job.get('arg_1')

        job_host.cmd('ping -c 1 ' + str(arg1))


    elif job_id == 2:
        arg_opt = job.get('arg_1')
        arg_ip = job.get('arg_2')

        if arg_opt:
            arg_opt = re.sub(r'[^\x00-\x7F]', '', arg_opt)

        if not arg_ip:
            print("No IP for a ping (with options) command")
            print(job)
            return

        job_host.cmd('ping -c 1 ' + str(arg_opt) + " " + str(arg_ip))

    # Sending UDP data
    elif job_id == 3:
        arg_size = job.get('arg_1')
        arg_ip = job.get('arg_2')
        arg_port = job.get('arg_3')

        if not arg_size:
            arg_size = 1000

        if int(arg_size) <= 0 or int(arg_size) > 65535:
            arg_size = 1000

        if not arg_ip:
            print("No IP for a sending UDP data command")
            print(job)
            return

        if not arg_port:
            print("No port for a sending UDP data command")
            print(job)
            return

        job_host.cmd(
            'dd if=/dev/urandom bs=' + str(arg_size) + ' count=1 | nc -uq1 ' + str(arg_ip) + ' ' + str(arg_port))


    elif job_id == 4:
        arg_size = job.get('arg_1')
        arg_ip = job.get('arg_2')
        arg_port = job.get('arg_3')

        if not arg_size:
            arg_size = 1000

        if int(arg_size) <= 0 or int(arg_size) > 65535:
            arg_size = 1000

        if not arg_ip:
            print("NO IP for a sending TCP data command")
            print(job)
            return

        if not arg_port:
            print("No port for a sending TCP data command")
            print(job)
            return

        job_host.cmd(
            'dd if=/dev/urandom bs=' + str(arg_size) + ' count=1 | nc -w 30 -q1 ' + str(arg_ip) + ' ' + str(arg_port))


    elif job_id == 5:
        arg_opt = job.get('arg_1')
        arg_ip = job.get('arg_2')

        if arg_opt:
            arg_opt = re.sub(r'[^\x00-\x7F]', '', arg_opt)

        if not arg_ip:
            print("No IP for a traceroute -n (with options) command")
            print(job)
            return

        job_host.cmd('traceroute -n ' + str(arg_opt) + " " + str(arg_ip))


    elif job_id == 100:
        arg_ip = job.get('arg_2')
        arg_mask = job.get('arg_3')
        arg_dev = job.get('arg_1')

        if not arg_ip:
            print("No IP for ip add command")
            print(job)
            return

        if not arg_dev:
            print("No device for ip add command")
            print(job)
            return

        if arg_mask < 0 or arg_mask > 32:
            print("Invalid mask for ip add command")
            print(job)
            return

        job_host.cmd('ip addr add ' + str(arg_ip) + "/" + str(arg_mask) + " dev " + str(arg_dev))
        return

    elif job_id == 101:
        arg_dev = job.get('arg_1')

        if not arg_dev:
            print("No device for nat command")
            print(job)
            return

        job_host.cmd('iptables -t nat -A POSTROUTING -o ', arg_dev, '-j MASQUERADE')
        return

    elif job_id == 102:
        arg_ip = job.get('arg_1')
        arg_mask = job.get('arg_2')
        arg_router = job.get('arg_3')

        if not arg_ip:
            print("No IP for ip route add command")
            print(job)
            return

        if arg_mask < 0 or arg_mask > 32:
            print("Invalid mask for ip route add")
            print(job)
            return

        if not arg_router:
            print("No IP address for router")
            print(job)
            return

        job_host.cmd('ip route add ' + str(arg_ip) + "/" + str(arg_mask) + " via " + str(arg_router))
        return

    elif job_id == 103:
        arg_ip = job.get('arg_1')
        arg_mac = job.get('arg_2')

        if not arg_ip:
            print("No IP for a arp -s command")
            print(job)
            return

        if not arg_mac:
            print("No MAC address for a arp -s command")
            print(job)
            return

        job_host.cmd('arp -s ' + str(arg_ip) + " " + str(arg_mac))
        return

    # Open UDP server
    elif job_id == 200:
        arg_ip = job.get('arg_1')
        arg_port = job.get('arg_2')

        if not arg_ip:
            print("No IP for Open UDP server command")
            print(job)
            return

        if not arg_port:
            print("No port for Open UDP server command")
            print(job)
            return

        if int(arg_port) < 0 or int(arg_port) > 65535:
            print("Invalid port number for Open UDP server")
            print(job)
            return

        job_host.cmd('nohup nc -d -u ' + str(arg_ip) + ' -l ' + str(arg_port) + ' > /tmp/udpserver 2>&1 < /dev/null &')

    # Open TCP server
    elif job_id == 201:
        arg_ip = job.get('arg_1')
        arg_port = job.get('arg_2')

        if not arg_ip:
            print("No IP for Open TCP server command")
            print(job)
            return

        if not arg_port:
            print("No port for Open TCP server command")
            print(job)
            return

        if int(arg_port) < 0 or int(arg_port) > 65535:
            print("Invalid port number for Open TCP server")
            print(job)
            return

        job_host.cmd('nohup nc -k -d ' + str(arg_ip) + ' -l ' + str(arg_port) + ' > /tmp/tcpserver 2>&1 < /dev/null &')

    # Block TCP/UDP port
    elif job_id == 202:
        arg_port = job.get('arg_1')

        if not arg_port:
            print("No port for Block TCP/UDP port command")
            print(job)
            return

        if int(arg_port) < 0 or int(arg_port) > 65535:
            print("Invalid port number for Block TCP/UDP port")
            print(job)
            return

        job_host.cmd('iptables -A INPUT -p tcp --dport ' + str(arg_port) + ' -j DROP')
        job_host.cmd('iptables -A INPUT -p udp --dport ' + str(arg_port) + ' -j DROP')


def run_mininet(net, net_guid):
    global jnet
    global time_to_wait_before_emulation

    animation = []
    jnet = json.loads(net)

    if not jnet.get('jobs'):
        return animation

    topo = MyTopology()
    net = IPNet(topo=topo, use_v6=False, autoSetMacs=True, allocate_IPs=False)

    # Disable IPv6 and TSO and enable source route
    for h in net.hosts:
        # print ("disable ipv6 on " + h.name)
        h.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
        h.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        h.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")
        h.cmd("sysctl -w net.ipv4.tcp_min_tso_segs=1")
        h.cmd("sysctl -w net.ipv4.conf.all.accept_source_route=1")
        h.cmd("sysctl -w net.ipv4.conf.all.log_martians=1")

    # Enable source route
    for r in net.routers:
        r.cmd("sysctl -w net.ipv4.conf.all.accept_source_route=1")
        r.cmd("sysctl -w net.ipv4.conf.all.log_martians=1")

    for sw in net.switches:
        # print ("disable ipv6 on " + sw.name)
        sw.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
        sw.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        sw.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")

    net.start()
    time.sleep(time_to_wait_before_emulation)
    # IPCLI(net)

    # Don only 100+ jobs
    for job in jnet['jobs']:

        if not type(job) is dict:
            print(job)
            print("Job is not a dict")
            continue

        job_id = job.get('job_id')
        if not job_id:
            print(job)
            print("Job id is missing")
            continue

        if int(job_id) < 100:
            continue

        host_id = job.get('host_id')
        if not host_id:
            print(job)
            print("host_id is missing")
            continue

        try:
            job_host = net.get(host_id)
        except KeyError as key:
            print("We got job for " + str(host_id) + ", but host not found")
            continue

        if job_host:
            do_job(job, job_host)

    # Do only job_id < 100
    for job in jnet['jobs']:

        if not type(job) is dict:
            print(job)
            print("Job is not a dict")
            continue

        job_id = job.get('job_id')
        if not job_id:
            print(job)
            print("Job id is missing")
            continue

        if int(job_id) >= 100:
            continue

        host_id = job.get('host_id')
        if not host_id:
            print(job)
            print("host_id is missing")
            continue

        try:
            job_host = net.get(host_id)

        except KeyError as ke:
            print("We got job for " + str(host_id) + ", but host not found")
            continue

        if job_host:

            try:
                do_job(job, job_host)

            except Exception as e:
                print("Current job:" + str(job))
                print(e)

    # IPCLI(net)
    # net.ping(use_v6=Fale)
    time.sleep(2)
    net.stop()

    # Create directory for a PCAP files
    net_directory = 'static/pcaps/' + str(net_guid)

    if not os.path.exists(net_directory):
        os.makedirs(net_directory)
    else:
        shutil.rmtree(net_directory)
        os.makedirs(net_directory)

    pcap_list = []
    # Parsing packets
    # Loop throught the links
    for lp in topo.link_pair:
        link1 = lp[0]
        link2 = lp[1]
        edge_id = lp[2]
        e_source = lp[3]
        e_target = lp[4]

        pcap_file1 = '/tmp/capture_' + link1 + '.pcapng'
        pcap_file2 = '/tmp/capture_' + link2 + '.pcapng'

        if not os.path.exists(pcap_file1):
            raise ValueError("No capture for interface: " + link1)

        if not os.path.exists(pcap_file2):
            raise ValueError("No capture for interface: " + link2)

        with open(pcap_file1, 'rb') as file:
            pcap_list.append((file.read(), link1))

        with open(pcap_file2, 'rb') as file:
            pcap_list.append((file.read(), link2))

        # print ("link1:" + pcap_file1 + '| link2:' + pcap_file2)
        pkts = create_pkt_animation(pcap_file1, pcap_file2, edge_id, e_source, e_target)
        animation += pkts

        # Rename files in the end.
        # We don't wanna use this files in future
        os.remove(pcap_file1)
        os.remove(pcap_file2)
        os.system('chown -R ilya:ilya ' + net_directory)
        # print (pkts)

    animation_s = sorted(animation, key=lambda k: k.get('timestamp', 0))

    if animation_s:

        animation = []
        animation_m = []
        first_packet = None
        limit = 0

        # Magic constant.
        # Number of microseconds * 100000
        # Depends on 'opts1["params2"] = {"delay": delay' in addLink function
        pkt_speed = 14000

        for pkt in animation_s:

            if not first_packet:
                first_packet = pkt
                animation_m = [pkt]
                limit = int(first_packet['timestamp']) + pkt_speed
                continue

            if int(pkt['timestamp']) > limit:
                animation.append(animation_m)
                first_packet = pkt
                animation_m = [pkt]
                limit = int(first_packet['timestamp']) + pkt_speed
                continue

            animation_m.append(pkt)

        # Append last packet
        animation.append(animation_m)

    # Waitng for shuting down switches and hosts
    time.sleep(2)
    print("End simulation")

    # Shut down running services
    os.system("ps -C nc -o pid=|xargs kill -9")

    # Return animation
    return animation, pcap_list


# def simulation_check():
#     print("Check for a new simulation request")
#     with app.app_context():
#         sim = Simulate.query.filter(Simulate.ready == 0).first()
#
#         if not sim:
#             return
#
#         net = Network.query.filter(Network.id == sim.network_id).first()
#
#         # We got simulation and don't have a corresponding network.
#         # Log it and delete simulation
#         if not net:
#             print("We got simulation and don't have c corresponding network")
#             db.session.delete(sim)
#             db.session.commit()
#             return
#
#         # Gets SimulateLog record
#         simlog = SimulateLog.query.filter(SimulateLog.network_guid == net.guid).order_by(SimulateLog.id.desc()).first()
#
#         try:
#
#             print("Network guid: " + str(net.guid))
#             res = run_mininet(net.network, net.guid)
#
#             sim.packets = json.dumps(res)
#             sim.ready = True
#
#             if simlog:
#                 if not simlog.ready:
#                     simlog.ready = True
#
#             db.session.commit()
#
#         except ValueError as e:
#             print("Simulation error:" + str(e))
#
#         except StaleDataError as e:
#             print("Looks like user update his network while it simulated. Skip...")
#             print(e)
#
#         return
#
#
# def miminet_polling():
#     while True:
#         simulation_check()
#         time.sleep(1)
#
#
# if __name__ == '__main__':
#
#     setLogLevel('info')
#
#     if os.name == 'posix':
#         print("Set default handler to SIGCHLD")
#         signal.signal(signal.SIGCHLD, signal.SIG_IGN)
#
#     miminet_polling()
