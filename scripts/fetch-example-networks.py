#!/usr/bin/env python3
"""Fetch the public example networks from miminet.ru into back/bench/examples/.

The "/examples" page networks are stored only in the deployed PostgreSQL
database, but each one is served to anonymous visitors at
``/web_network_shared?guid=<guid>`` with the full network definition embedded
in the page as ``var nodes``, ``const edges`` and ``var jobs`` JS literals
(plus ``network_zoom`` / ``network_pan_x`` / ``network_pan_y``).

This script reconstructs the canonical benchmark JSON
(``{nodes, edges, jobs, config, packets:"", pcap:[]}``) for each example and
writes it to ``back/bench/examples/<slug>_network.json`` so the benchmark
harness can consume it unchanged (``bench.py --networks <dir>`` globs
``*_network.json``).

Usage:
    python3 scripts/fetch-example-networks.py [--out DIR]
"""

import argparse
import ast
import json
import re
import sys
import urllib.request
from pathlib import Path

BASE_URL = "https://miminet.ru/web_network_shared"

# (guid, slug) as listed on the public /examples page.
EXAMPLES = [
    ("d5eb566d-402e-442f-a98a-d5341568a5c9", "switch_and_hub"),
    ("385ccc51-9a6e-4b9a-8e90-fbf27ae73186", "router"),
    ("19e7c6b6-9541-4602-8c78-d0c64c069b41", "nat_2"),
    ("7509b963-d190-4aad-8d90-9be42f302bbb", "ring_of_3_routers"),
    ("076f1ae4-1a6d-42fd-b8f5-9c09cdc4f930", "first_and_last_ip_address"),
    ("d35bcad2-b2be-4c2a-9902-26d4edd0bb1d", "tcp_connection_setup_1"),
    ("6994b921-cc0f-4cbd-b209-7f30784027d7", "icmp_network_unavailable"),
    ("1646e111-1a47-4d98-a253-c396904e5351", "icmp_host_unreachable"),
    ("4fc0fafb-2a16-4244-a664-3f1e8f788a63", "multicast_udp"),
    ("0a1be702-d7fb-4e97-a8ae-fe9cb75fcf32", "stp"),
    ("1ccd87d4-a74f-485e-a95e-e1111c041fc7", "vlan"),
    ("fe1fc02f-6bb4-421d-94cb-6902f826e30d", "ipip_tunnel"),
    ("993e2d62-ae6c-4b62-9ec4-6d90f768b56a", "vxlan"),
]


def fetch_page(guid: str) -> str:
    url = f"{BASE_URL}?guid={guid}"
    req = urllib.request.Request(url, headers={"User-Agent": "miminet-bench"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.url != url:
            raise RuntimeError(f"redirected to {resp.url} (not share_mode?)")
        return resp.read().decode("utf-8")


def extract_var(html: str, varname: str, kind: str):
    """Capture a JS variable body from the page and parse it."""
    pattern = rf"(?:const|var)\s+{varname}\s*=\s*(.*?);\s*\n"
    m = re.search(pattern, html, re.DOTALL)
    if not m:
        raise RuntimeError(f"variable '{varname}' not found")
    text = m.group(1).strip()
    if kind == "json":
        return json.loads(text)
    if kind == "literal":
        return ast.literal_eval(text)
    return text


def build_network_json(html: str) -> dict:
    nodes = extract_var(html, "nodes", "json")
    edges = extract_var(html, "edges", "literal")
    jobs = extract_var(html, "jobs", "literal")
    zoom = extract_var(html, "network_zoom", "scalar")
    pan_x = extract_var(html, "network_pan_x", "scalar")
    pan_y = extract_var(html, "network_pan_y", "scalar")
    return {
        "nodes": nodes,
        "edges": edges,
        "jobs": jobs,
        "config": {"zoom": float(zoom), "pan_x": float(pan_x), "pan_y": float(pan_y)},
        "packets": "",
        "pcap": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent.parent / "back" / "bench" / "examples"),
        help="output directory for *_network.json files",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    for guid, slug in EXAMPLES:
        out_path = out_dir / f"{slug}_network.json"
        try:
            html = fetch_page(guid)
            net = build_network_json(html)
        except Exception as e:  # noqa: BLE001
            print(f"[fetch] {slug:<24} FAILED: {e!r}", flush=True)
            continue
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(net, fh, ensure_ascii=False, indent=4)
        print(
            f"[fetch] {slug:<24} nodes={len(net['nodes']):<3} "
            f"edges={len(net['edges']):<3} jobs={len(net['jobs']):<2} -> {out_path}",
            flush=True,
        )
        ok += 1

    print(f"[fetch] wrote {ok}/{len(EXAMPLES)} examples to {out_dir}", flush=True)
    sys.exit(0 if ok == len(EXAMPLES) else 1)


if __name__ == "__main__":
    main()
