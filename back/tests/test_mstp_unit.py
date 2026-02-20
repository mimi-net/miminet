import sys
from types import SimpleNamespace

sys.modules["ipmininet"] = SimpleNamespace()  # type: ignore
sys.modules["ipmininet.ipnet"] = SimpleNamespace(IPNet=object)  # type: ignore
sys.modules["ipmininet.ipswitch"] = SimpleNamespace(IPSwitch=object)  # type: ignore

sys.path.append("../src")

from net_utils.mstp import get_mst_instance_for_vlan


def test_vlan_to_mst_instance_mapping():
    mst_instances = [
        SimpleNamespace(instance_id=1, vlans=[10, 20]),
        SimpleNamespace(instance_id=2, vlans=[30]),
    ]

    node = SimpleNamespace(config=SimpleNamespace(mst_instances=mst_instances))

    assert get_mst_instance_for_vlan(node, 10) == 1
    assert get_mst_instance_for_vlan(node, 20) == 1
    assert get_mst_instance_for_vlan(node, 30) == 2
    assert get_mst_instance_for_vlan(node, 40) == 0
