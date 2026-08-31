#!/usr/bin/env python3
"""bench.py — measure Miminet emulation cost per network.

Drives the real emulation path (MiminetTopology -> MiminetNetwork ->
jobs -> create_animation) and records, per network JSON:

  * wall-clock per phase: net.start(), each job, net.stop(), pcap parse
    (create_animation)
  * process-tree peak RSS + CPU time (user+sys) of this process and all
    children (hosts, mimidump, routers)
  * ovs-vswitchd RSS delta (baseline before run, after run)

Run inside the emulation container with PYTHONPATH pointing at ../src:

    PYTHONPATH=/repo/back/src python3 /repo/back/bench/bench.py \
        --networks /repo/back/tests/test_json --repeats 1 --out /repo/.bench/report.json
"""

import argparse
import glob
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

SRC_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)
sys.path.insert(0, SRC_DIR)

import psutil  # noqa: E402
from mininet.log import setLogLevel  # noqa: E402

from emulator import create_animation, execute_job  # noqa: E402
from network import MiminetNetwork  # noqa: E402
from network_topology import MiminetTopology  # noqa: E402
import tasks  # noqa: E402


def setup():
    if os.name == "posix":
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    setLogLevel("info")


def cleanup_pcap_files():
    for f in glob.glob("/tmp/capture_*.pcapng"):
        try:
            os.remove(f)
        except OSError:
            pass


def cleanup_emulation():
    subprocess.call(
        "mn -c", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def ovs_vswitchd_rss():
    """Return current RSS (bytes) of the ovs-vswitchd daemon, or None."""
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] == "ovs-vswitchd":
                return proc.memory_info().rss
        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ProcessLookupError,
            psutil.ZombieProcess,
        ):
            continue
    return None


class Sampler:
    """Background thread sampling process-tree RSS."""

    def __init__(self, interval: float = 0.1):
        self.interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.peak_rss = 0

    def _run(self):
        root = psutil.Process()
        while not self._stop.is_set():
            try:
                total = root.memory_info().rss
                for child in root.children(recursive=True):
                    try:
                        total += child.memory_info().rss
                    except (
                        psutil.NoSuchProcess,
                        psutil.AccessDenied,
                        psutil.ProcessLookupError,
                        psutil.ZombieProcess,
                    ):
                        pass
                self.peak_rss = max(self.peak_rss, total)
            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ProcessLookupError,
                psutil.ZombieProcess,
            ):
                break
            self._stop.wait(self.interval)

    def start(self):
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=10)


def load_network(network_json: str):
    """Load and validate a network JSON like tasks.run_miminet does."""
    jnet = tasks._filter_unknown_nodes(json.loads(network_json))
    schema = tasks.get_network_schema()
    return schema.load(jnet, unknown="include")


def run_once(network, name: str = "network"):
    """Run one emulation, returning the metrics dict."""
    cleanup_pcap_files()
    cleanup_emulation()
    ovs_baseline = ovs_vswitchd_rss()

    topo = MiminetTopology(network)
    net = MiminetNetwork(topo, network)

    sampler = Sampler()
    sampler.start()
    cpu_start = psutil.Process().cpu_times()

    wall_start = time.monotonic()
    try:
        net.start()
        ordered_jobs = sorted(network.jobs, key=lambda j: j.job_id // 100, reverse=True)
        job_times = {}
        for job in ordered_jobs:
            t0 = time.monotonic()
            execute_job(job, net)
            job_times[f"{job.host_id}:{job.job_id}:{job.print_cmd}"] = (
                time.monotonic() - t0
            )
        t0 = time.monotonic()
        net.stop()
        stop_time = time.monotonic() - t0
    except Exception:
        cleanup_emulation()
        raise

    t0 = time.monotonic()
    create_animation(topo.interfaces)
    parse_time = time.monotonic() - t0

    wall = time.monotonic() - wall_start
    sampler.stop()
    cpu = psutil.Process().cpu_times()
    cpu_used = (cpu.user - cpu_start.user) + (cpu.system - cpu_start.system)

    pcap_sizes = {
        os.path.basename(f): os.path.getsize(f)
        for f in glob.glob("/tmp/capture_*.pcapng")
    }

    return {
        "wall": wall,
        "stop_time": stop_time,
        "settle_hit_cap": net.settle_hit_cap,
        "jobs": job_times,
        "parse_time": parse_time,
        "peak_rss": sampler.peak_rss,
        "cpu_time": cpu_used,
        "ovs_rss_baseline": ovs_baseline,
        "ovs_rss_after": ovs_vswitchd_rss(),
        "pcap_sizes": pcap_sizes,
        "n_nodes": len(network.nodes),
        "n_edges": len(network.edges),
        "n_jobs": len(network.jobs),
    }


def main():
    setup()
    parser = argparse.ArgumentParser(description="Miminet emulation benchmark")
    parser.add_argument(
        "--networks",
        required=True,
        help="dir of *_network.json or comma-separated explicit file list",
    )
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--out", required=True, help="JSON report output path")
    parser.add_argument("--quiet", action="store_true", help="suppress per-run prints")
    args = parser.parse_args()

    src = Path(args.networks)
    if src.is_dir():
        paths = sorted(src.glob("*_network.json"))
    else:
        paths = [Path(p.strip()) for p in args.networks.split(",") if p.strip()]

    report = {"mode": os.environ.get("BACK_MODE", "boxed"), "networks": {}}
    for path in paths:
        name = path.stem.removesuffix("_network")
        with open(path) as fh:
            try:
                network = load_network(fh.read())
            except Exception as e:
                report["networks"][name] = [{"error": repr(e)}]
                print(f"[bench] {name} SKIPPED (load error: {e!r})", flush=True)
                continue
        runs = []
        for i in range(args.repeats):
            try:
                metrics = run_once(network, name)
                runs.append(metrics)
                if not args.quiet:
                    print(
                        f"[bench] {name} run={i} wall={metrics['wall']:.2f}s "
                        f"peak_rss={metrics['peak_rss'] / 2**20:.1f}MiB "
                        f"cpu={metrics['cpu_time']:.2f}s",
                        flush=True,
                    )
            except Exception as e:
                runs.append({"error": repr(e)})
                print(f"[bench] {name} run={i} FAILED: {e!r}", flush=True)
        report["networks"][name] = runs

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as fh:
        json.dump(report, fh, indent=2)
    print(f"[bench] report written to {out}", flush=True)


if __name__ == "__main__":
    main()
