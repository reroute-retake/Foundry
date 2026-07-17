---
name: foundry-status
description: Read-only Pipeline Ledger status report — what is next and what is blocked, per batch. The sanctioned way to inspect ledger state; never read .skills-data/ files directly.
---

# foundry-status

The Operator's (and every role session's) view into the Pipeline Ledger:
node counts by state, quarantined and canonical lists, and document
extraction progress. Strictly read-only.

## Commands

```bash
python3 skills/foundry-status/scripts/run_status.py          # human-readable
python3 skills/foundry-status/scripts/run_status.py --json   # machine-readable
```

## Rules

- This script is the sanctioned read path for ledger state. Do not `cat`
  `.skills-data/` files directly — command-deny rules block that by design
  (register #49), and raw revision files are not the derived truth anyway.
- Mutates nothing; safe to run at any time, from any role session.
