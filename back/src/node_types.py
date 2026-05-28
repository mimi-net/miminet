from enum import Enum


class NodeType(str, Enum):
    """
    Types of all functional network nodes
    """

    HOST = "host"
    SERVER = "server"
    SWITCH = "l2_switch"
    HUB = "l1_hub"
    ROUTER = "router"
