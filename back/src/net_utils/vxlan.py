from ipmininet.ipnet import IPNet
from network import Node


def setup_vtep_interfaces(net: IPNet, nodes: list[Node]) -> None:
    for node in nodes:
        if node.config.type == "router":
            router = net.get(node.data.id)
            for iface in node.interface:
                vni = iface.vxlan
                connection_type = iface.connection_type
                target_ip = iface.target_ip
                if vni is not None:
                    if connection_type == 1:
                        setup_network_interface(router, iface.name, vni, iface.ip, target_ip)
            for iface in node.interface:
                vni = iface.vxlan
                connection_type = iface.connection_type
                if vni is not None:
                    if connection_type == 0:
                        setup_endpint_interface(router, iface.name, vni)


def setup_network_interface(router, intf: str, vni: int, local_ip: str,target_ip: str):
    vxlan = 'vx' + str(router.name) + '-' + str(vni)
    bridge = 'br-' + str(router.name) + '-' + str(vni)
    vxlan = vxlan[:15]
    bridge = bridge[:15]
    # commands = [
    #     f'ip link add {vxlan} type vxlan id {vni} local {local_ip} remote {target_ip} dstport 4789 dev {intf}',
    #     f'ip link set {vxlan} up',
    #     f'ip link add {bridge} type bridge',
    #     # f'ip link set {intf} master {bridge}',
    #     f'ip link set {vxlan} master {bridge}',
    #     f'ip link set {bridge} up',
    #     f'ip link set dev {intf} up'
    # ]
    commands = [
        f'ip link add {vxlan} type vxlan id {vni} local {local_ip} dstport 4789 dev {intf}',
        f'ip link set {vxlan} up',
        f'brctl addbr {bridge}',
        f'bridge fdb append 00:00:00:00:00:00 dev {vxlan} dst {target_ip}',
        # f'ip link set {intf} master {bridge}',
        f'brctl addif {bridge} {vxlan}',
        f'brctl stp {bridge} off',
        f'ip link set {bridge} up',
    ]
    for cmd in commands:
        try:
            print(f"Executing command: {cmd}")
            output = router.cmd(cmd)
            if output:
                print(f"Command output: {output}")
        except Exception as e:
            print(f"Failed to execute command '{cmd}': {e}")

def setup_endpint_interface(router, intf: str, vni: int):
    bridge = 'br-' + str(router.name) + '-' + str(vni)
    bridge = bridge[:15]
    commands = [
        f'brctl addif {bridge} {intf}',
        f'ip link set dev {intf} up'
    ]
    for cmd in commands:
        try:
            print(f"Executing command: {cmd}")
            output = router.cmd(cmd)
            if output:
                print(f"Command output: {output}")
        except Exception as e:
            print(f"Failed to execute command '{cmd}': {e}")



# def configure_interface(router, intf: str, vni: int, target_ip: str) -> None:
#     # vxlan = 'vxlan'+intf
#     # router.cmd(f'ip link add {vxlan} type vxlan id {vni} remote {target_ip} dstport 4789 dev {intf}')
#     # router.cmd(f'ip link add br-{intf} type bridge')
#     # router.cmd(f'ip link set {intf} master br-{intf}')
#     # router.cmd(f'ip link set {vxlan} master br-{intf}')
#     # router.cmd(f'ip link set dev br-{intf} up')
#     # router.cmd(f'ip link set dev {intf} up')
#     vxlan = 'vx' + intf[:13]  # Обрежьте имя до 15 символов, включая 'vx'
#     bridge = 'br' + intf[:11]  # Обрежьте имя до 15 символов, включая 'br-'
#     commands = [
#         f'ip link add {vxlan} type vxlan id {vni} remote {target_ip} dstport 4789 dev {intf}',
#         f'ip link set {vxlan} up',
#         f'ip link add {bridge} type bridge',
#         f'ip link set {intf} master {bridge}',
#         f'ip link set {vxlan} master {bridge}',
#         f'ip link set dev {bridge} up',
#         f'ip link set dev {intf} up'
#     ]
#
#     for cmd in commands:
#         try:
#             print(f"Executing command: {cmd}")
#             output = router.cmd(cmd)
#             if output:
#                 print(f"Command output: {output}")
#         except Exception as e:
#             print(f"Failed to execute command '{cmd}': {e}")
