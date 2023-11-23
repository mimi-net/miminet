# Classes for deserialize miminet network
# Classes for deserialize miminet network

from dataclasses import dataclass


@dataclass
class NodeData:
    """NodeData

    Args:
        id (int): node id
        label (str): node label

    """

    id: str
    label: str


@dataclass
class NodeConfig:
    """NodeConfig

    Args:
        label (str): node label (for example, l2sw1)
        type (str): node type (for example, l2_switch)
        stp (int): 1 if need stp
        default_gw (str): default gateway

    """

    label: str = ""
    type: str = ""
    stp: int = 0
    default_gw: str = ""


@dataclass
class NodeInterface:
    """NodeInterface

    Args:
        connect (str): node label (for example, l2sw1)
        id (str): interface id (for example, l2sw1_1)
        name (str): interface name (for example, l2sw1_1)
        ip (str): ip (for example, 10.0.0.1)
        netmask (str): netmask

    """

    connect: str
    id: str
    name: str = ""
    ip: str = ""
    netmask: int = 0


@dataclass
class NodePosition:
    """NodePosition

    Args:
        x (float): x node position
        y (float): y node position

    """

    x: float
    y: float


@dataclass
class Node:
    """Node

    Args:
        config (NodeConfig): NodeConfig instance
        data (NodeData) : NodeData instance
        interface (list[NodeInterface]): list of NodeInterface instance
        position (NodePosition): NodePosition instance
        classes (list[str]): for example(["l2_switch"])

    """

    config: NodeConfig
    data: NodeData
    interface: list[NodeInterface]
    classes: list[str]
    position: NodePosition


@dataclass
class EdgeData:
    """EdgeData

    Args:
        id (str): edge id
        source (str) : edge source (for example, "host_2")
        target (str): edge target (for example, "l1hub1")

    """

    id: str
    source: str
    target: str


@dataclass
class Edge:
    """Edge

    Args:
        data (EdgeData): EdgeData instance

    """

    data: EdgeData


@dataclass
class Job:
    """Job

    Args:
        id (str): str job id
        level (int): job level
        job_id (int): int job id (for execute)
        host_id (str): host id for job executing (for example, host_1)
        arg_1 (str): parameter for job executing (for example, ip, port, netmask, ...)
        arg_2 (str): parameter for job executing
        arg_3 (str): parameter for job executing
    """

    id: str
    level: int
    job_id: int
    host_id: str
    print_cmd: str
    arg_1: str | int = ""
    arg_2: str | int = ""
    arg_3: str | int = ""


@dataclass
class NetworkConfig:
    """Job

    Args:
        zoom (float): zoom
        pan_x (float): pan-x
        pan_y (float): pan-y

    """

    zoom: float
    pan_x: float
    pan_y: float


@dataclass
class Network:
    """Job

    Args:
        nodes (list[Node]): list of Node instance
        edges (list[Edge]): list of Edges instance
        jobs (list[Job]): list of Jobs instance
        config (NetworkConfig): NetworkConfig instance
        packets (str): packets
        pcap (list[str]): pcaps

    """

    nodes: list[Node]
    edges: list[Edge]
    jobs: list[Job]
    config: NetworkConfig
    pcap: list[str]
    packets: str = ""
