from __future__ import annotations

import argparse
import json
import os
import signal
import statistics as stats
from pathlib import Path
from typing import Any, Dict, List


def load_network(path: str):
    """Load network configuration from JSON file.

    Args:
        path: Path to network JSON file

    Returns:
        Network object
    """
    try:
        import marshmallow_dataclass  # type: ignore
    except ImportError:
        import sys

        print("[ERROR] marshmallow_dataclass package not found.")
        print("Current interpreter:", sys.executable)
        print("Install with:")
        print(
            f"  {sys.executable} -m pip install marshmallow-dataclass==8.7.1 marshmallow"
        )
        raise SystemExit(1)

    from network_schema import Network

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    schema = marshmallow_dataclass.class_schema(Network)()
    return schema.load(data, unknown="include")


def run_once(network, network_name: str) -> Dict[str, float]:
    """Run emulation once and return timing results.

    Args:
        network: Network configuration object
        network_name: Name of the network (for logging)

    Returns:
        Dictionary with stage timings
    """
    import subprocess
    import time
    from benchmarking import StageTimer
    from emulator import emulate

    timer = StageTimer()

    try:
        subprocess.run(
            ["mn", "-c"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        time.sleep(0.5)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    if os.name == "posix":
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    print(f"  Running emulation for '{network_name}'...")

    try:
        emulate(network, timer=timer)
    except Exception as e:
        try:
            subprocess.run(
                ["mn", "-c"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        except Exception:
            pass
        raise e

    try:
        subprocess.run(
            ["mn", "-c"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        time.sleep(0.5)
    except Exception:
        pass

    return timer.as_dict()


def format_report(
    results: Dict[str, List[Dict[str, float]]], iterations: int
) -> tuple[str, dict]:
    """Format benchmark results as text report and JSON.

    Args:
        results: Dictionary mapping network names to lists of timing dictionaries
        iterations: Number of iterations per network

    Returns:
        Tuple of (text_report, json_data)
    """
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("MIMINET EMULATION BENCHMARK REPORT")
    report_lines.append("=" * 80)
    report_lines.append(f"Iterations per network: {iterations}")
    report_lines.append(f"Networks tested: {len(results)}")
    report_lines.append("")

    json_data: Dict[str, Any] = {"iterations_per_network": iterations, "networks": []}

    for network_name, runs in results.items():
        report_lines.append("-" * 80)
        report_lines.append(f"Network: {network_name}")
        report_lines.append("-" * 80)

        # Collect all stage names
        keys = sorted({k for r in runs for k in r.keys()})

        # Aggregate timings
        agg: Dict[str, List[float]] = {k: [] for k in keys}
        for r in runs:
            for k in keys:
                agg[k].append(r.get(k, 0.0))

        # Calculate totals
        totals = [sum(r.values()) for r in runs]
        tot_mean = stats.mean(totals) if totals else 0.0
        tot_std = stats.stdev(totals) if len(totals) > 1 else 0.0

        report_lines.append(f"Total time (mean): {tot_mean:.3f}s ± {tot_std:.3f}s")
        report_lines.append("")

        # Stage details
        width = max((len(k) for k in keys), default=20)
        header = (
            f"{'Stage'.ljust(width)}  {'Mean(s)':>9}  {'Std(s)':>8}  {'Share(%)':>9}"
        )
        report_lines.append(header)
        report_lines.append("-" * len(header))

        network_json: Dict[str, Any] = {
            "name": network_name,
            "total_mean_sec": tot_mean,
            "total_std_sec": tot_std,
            "stages": [],
        }

        for k in keys:
            vals = agg[k]
            mean = stats.mean(vals) if vals else 0.0
            std = stats.stdev(vals) if len(vals) > 1 else 0.0
            share = (mean / tot_mean * 100.0) if tot_mean > 0 else 0.0

            line = f"{k.ljust(width)}  {mean:9.3f}  {std:8.3f}  {share:9.2f}"
            report_lines.append(line)

            stage_info: Dict[str, Any] = {
                "name": k,
                "mean_sec": mean,
                "std_sec": std,
                "share_percent": share,
            }
            network_json["stages"].append(stage_info)

        report_lines.append("")
        json_data["networks"].append(network_json)

    report_lines.append("=" * 80)

    return "\n".join(report_lines), json_data


def check_requirements():
    if os.name == "posix" and os.geteuid() != 0:
        print("[ERROR] Mininet must be run as root.")
        print("Run with: sudo -E python3 back/src/benchmark_emulation.py ...")
        print("Or: open root shell (sudo -s), activate venv, then run.")
        return False

    for bin_name in ("mnexec", "mn"):
        if not any(
            os.path.exists(os.path.join(p, bin_name))
            and os.access(os.path.join(p, bin_name), os.X_OK)
            for p in os.get_exec_path()
        ):
            print(
                f"[ERROR] Binary '{bin_name}' not found. Mininet not installed or not in PATH."
            )
            print("Install (Ubuntu/Debian):")
            print("  sudo apt-get update && sudo apt-get install -y mininet")
            return False

    if not any(
        os.path.exists(os.path.join(p, "brctl"))
        and os.access(os.path.join(p, "brctl"), os.X_OK)
        for p in os.get_exec_path()
    ):
        print("[ERROR] 'brctl' not found. Install bridge-utils package.")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Run Miminet emulation benchmark and report stage timings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single network, 5 iterations (default)
  sudo python3 benchmark_emulation.py --networks back/tests/test_json/router_network.json
  
  # Multiple networks, 10 iterations
  sudo python3 benchmark_emulation.py \\
    --networks back/tests/test_json/router_network.json \\
              back/tests/test_json/switch_and_hub_network.json \\
    --iterations 10 \\
    --output-file benchmark_results.txt
        """,
    )
    parser.add_argument(
        "--networks",
        nargs="+",
        required=True,
        metavar="JSON_FILE",
        help="Path(s) to network JSON file(s) to benchmark",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Number of iterations per network (default: 5)",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="",
        help="Output file for text report (JSON will be saved as <name>.json)",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue benchmark even if some iterations fail",
    )
    args = parser.parse_args()

    if args.iterations < 1:
        print(f"[ERROR] Iterations must be >= 1, got {args.iterations}")
        return 1

    if not check_requirements():
        return 1

    for network_path in args.networks:
        if not os.path.exists(network_path):
            print(f"[ERROR] Network file not found: {network_path}")
            return 1

    print(
        f"Starting benchmark with {len(args.networks)} network(s), {args.iterations} iteration(s) each"
    )
    print()

    all_results: Dict[str, List[Dict[str, float]]] = {}

    for network_path in args.networks:
        network_name = Path(network_path).stem
        print(f"Loading network: {network_name}")

        try:
            network = load_network(network_path)
        except Exception as e:
            print(f"[ERROR] Failed to load network '{network_path}': {e}")
            return 1

        runs: List[Dict[str, float]] = []
        failed_iterations = 0

        for i in range(args.iterations):
            print(f"  Iteration {i+1}/{args.iterations}")
            try:
                result = run_once(network, network_name)
                runs.append(result)
            except Exception as e:
                failed_iterations += 1
                print(f"[WARNING] Iteration {i+1} failed: {e}")
                if args.continue_on_error:
                    print("[INFO] Continuing with remaining iterations...")
                    continue
                else:
                    print(
                        "[ERROR] Stopping benchmark (use --continue-on-error to continue)"
                    )
                    return 1

        if len(runs) == 0:
            print(f"[ERROR] All iterations failed for {network_name}")
            return 1

        if failed_iterations > 0:
            print(
                f"[WARNING] {failed_iterations}/{args.iterations} iterations failed, using {len(runs)} successful runs"
            )

        all_results[network_name] = runs
        print(f"  Completed {network_name}")
        print()

    text_report, json_data = format_report(all_results, args.iterations)

    print(text_report)

    if args.output_file:
        txt_path = args.output_file
        json_path = (
            txt_path + ".json"
            if not txt_path.endswith(".json")
            else txt_path.replace(".txt", ".json")
        )

        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text_report + "\n")
            print(f"Text report saved: {txt_path}")

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            print(f"JSON report saved: {json_path}")
        except OSError as e:
            print(f"[ERROR] Failed to write report files: {e}")
            return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    raise SystemExit(exit_code)
