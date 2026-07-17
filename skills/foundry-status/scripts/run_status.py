"""Per-batch Pipeline Ledger status report (ADR 017's ``status``).

Read-only — folds the event log under the ledger lock (a consistent snapshot;
never a mid-append read) and prints what is next and what is blocked. Mutates
nothing.

Usage:
    python3 skills/foundry-status/scripts/run_status.py [--json]
"""

import argparse
import json
from dataclasses import asdict

import _bootstrap

import status
import workspace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    root = _bootstrap.data_root()
    with workspace.ledger_lock(root):
        report = status.build_report(root)

    if args.json:
        print(json.dumps(asdict(report), sort_keys=True))
    else:
        print(report.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
