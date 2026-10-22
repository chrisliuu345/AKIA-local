#!/usr/bin/env python3
"""Compare normal AQL plans with an independent MIT-licensed reference table."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.sampling_engine import SamplingEngine  # noqa: E402

REFERENCE = ROOT / "tests" / "fixtures" / "aql_reference_mit.json"
LOTS = {
    "A": (5, "II"), "B": (12, "II"), "C": (20, "II"), "D": (30, "II"),
    "E": (70, "II"), "F": (120, "II"), "G": (200, "II"), "H": (400, "II"),
    "J": (600, "II"), "K": (2000, "II"), "L": (5000, "II"),
    "M": (20000, "II"), "N": (100000, "II"), "P": (300000, "II"),
    "Q": (700000, "II"), "R": (700000, "III"),
}


def _reference_key(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def compare(reference_path: str | Path = REFERENCE) -> dict:
    payload = json.loads(Path(reference_path).read_text(encoding="utf-8"))
    mismatches = []
    arrow_cells = []
    checked = 0
    for code, (lot_size, level) in LOTS.items():
        for aql in payload["aqls"]:
            expected = tuple(payload["plans"][code][_reference_key(aql)])
            result = SamplingEngine.aql_lookup(lot_size, aql, level)
            actual = (result["accept"], result["reject"])
            if result["via_arrow"]:
                arrow_cells.append({
                    "code": code,
                    "aql": aql,
                    "resolved_code": result["plan_code"],
                    "actual": list(actual),
                    "reference": list(expected),
                })
                continue
            checked += 1
            if actual != expected:
                mismatches.append({
                    "code": code,
                    "aql": aql,
                    "actual": list(actual),
                    "reference": list(expected),
                })
            expected_sample = payload["sample_sizes"][code]
            if result["sample_size"] != expected_sample:
                mismatches.append({
                    "code": code,
                    "aql": aql,
                    "actual_sample_size": result["sample_size"],
                    "reference_sample_size": expected_sample,
                })
    return {
        "ok": not mismatches,
        "source": payload["_source"],
        "source_commit": payload["_commit"],
        "direct_cells_checked": checked,
        "direct_mismatches": mismatches,
        "arrow_cells": arrow_cells,
        "arrow_accept_mismatches": sum(
            item["actual"] != item["reference"] for item in arrow_cells),
        "arrow_note": payload["_note"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AQL 独立参考表交叉核对")
    parser.add_argument("--reference", default=str(REFERENCE))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = compare(args.reference)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        state = "ok" if result["ok"] else "fail"
        print(f"[{state}] 独立 AQL 参考核对")
        print(f"  直接单元格: {result['direct_cells_checked']}，"
              f"不一致: {len(result['direct_mismatches'])}")
        print(f"  箭头单元格: {len(result['arrow_cells'])}（参考库未实现样本量迁移）")
        print(f"  其中 Ac/Re 差异: {result['arrow_accept_mismatches']}")
        for item in result["direct_mismatches"]:
            print(f"  - {item}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
