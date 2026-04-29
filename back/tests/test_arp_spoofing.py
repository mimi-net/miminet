from src.jobs import ARP_SPOOF_JOB_ID, Jobs
from src.network_schema import Job


class FakeNode:
    def __init__(self, name: str):
        self.name = name
        self.commands: list[str] = []

    def cmd(self, command: str) -> str:
        self.commands.append(command)
        return ""


def build_job(**kwargs) -> Job:
    return Job(
        id="job-arp-spoof",
        level=0,
        job_id=ARP_SPOOF_JOB_ID,
        host_id="hacker_1",
        print_cmd="ARP spoof test",
        arg_1=kwargs.get("arg_1", "hacker_1-eth0"),
        arg_2=kwargs.get("arg_2", "192.168.1.10"),
        arg_3=kwargs.get("arg_3", "192.168.1.1"),
        arg_4=kwargs.get("arg_4", "mitm"),
    )


def test_arp_spoof_job_starts_responder_and_enables_forwarding():
    hacker = FakeNode("hacker_1")

    Jobs(build_job(), hacker).handler()

    assert "sysctl -w net.ipv4.ip_forward=1" in hacker.commands
    assert "sysctl -w net.ipv4.conf.all.send_redirects=0" in hacker.commands
    assert "sysctl -w net.ipv4.conf.all.rp_filter=0" in hacker.commands
    assert "sysctl -w net.ipv4.conf.default.send_redirects=0" not in hacker.commands
    assert (
        "sysctl -w net.ipv4.conf.hacker_1-eth0.send_redirects=0" not in hacker.commands
    )
    assert "sysctl -w net.ipv4.conf.hacker_1-eth0.rp_filter=0" not in hacker.commands
    assert "iptables -P FORWARD ACCEPT" in hacker.commands
    assert any("arp_spoofer.py" in command for command in hacker.commands)
    assert any("--mode mitm" in command for command in hacker.commands)


def test_arp_spoof_job_reply_only_mode_starts_responder_without_forwarding():
    hacker = FakeNode("hacker_1")

    Jobs(build_job(arg_4="reply_only"), hacker).handler()

    assert "sysctl -w net.ipv4.ip_forward=0" in hacker.commands
    assert "iptables -P FORWARD ACCEPT" not in hacker.commands
    assert "sysctl -w net.ipv4.conf.all.send_redirects=0" not in hacker.commands
    assert any("--mode reply_only" in command for command in hacker.commands)


def test_arp_spoof_job_does_nothing_for_invalid_arguments():
    hacker = FakeNode("hacker_1")

    invalid_job = build_job(
        arg_1="bad iface", arg_2="192.168.1.10", arg_3="192.168.1.1"
    )

    Jobs(invalid_job, hacker).handler()

    assert hacker.commands == []


def test_arp_spoof_job_does_nothing_for_invalid_mode():
    hacker = FakeNode("hacker_1")

    invalid_mode_job = build_job(arg_4="unexpected_mode")

    Jobs(invalid_mode_job, hacker).handler()

    assert hacker.commands == []
