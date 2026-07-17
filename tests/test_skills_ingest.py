"""End-to-end CLI tests for the foundry-ingest and foundry-status skills.

Each test invokes the real scripts as subprocesses (the exact contract a
Tier-2 session uses), against a temp data root via the FOUNDRY_ROOT override.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REGISTER = REPO / "skills" / "foundry-ingest" / "scripts" / "register_document.py"
EXTRACT = REPO / "skills" / "foundry-ingest" / "scripts" / "extract_document.py"
STATUS = REPO / "skills" / "foundry-status" / "scripts" / "run_status.py"

CHAPTER = "# Chapter 5 — Replication\n\nLeaderless replication tolerates node outages.\n"


def _run(script: Path, *args: str, root: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, FOUNDRY_ROOT=str(root))
    return subprocess.run(
        [sys.executable, str(script), *[str(a) for a in args]],
        capture_output=True, text=True, env=env, timeout=60,
    )


def _source(tmp_path: Path, name: str = "ddia-ch5.md") -> Path:
    src = tmp_path / "works" / "sources" / name
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(CHAPTER, encoding="utf-8")
    return src


def test_register_then_extract_happy_path(tmp_path: Path) -> None:
    src = _source(tmp_path)

    reg = _run(REGISTER, src, root=tmp_path)
    assert reg.returncode == 0, reg.stderr
    reg_out = json.loads(reg.stdout)
    assert reg_out["ok"] and reg_out["document_id"] == "ddia_ch5"

    ext = _run(EXTRACT, src, root=tmp_path)
    assert ext.returncode == 0, ext.stderr
    ext_out = json.loads(ext.stdout)
    assert ext_out["ok"] and ext_out["sha256"] == reg_out["source_sha256"]

    # The artifact is a byte-identical copy under .skills-data/ (ADR 013).
    artifact = tmp_path / ".skills-data" / ext_out["artifact"]
    assert artifact.read_text(encoding="utf-8") == CHAPTER

    # The ledger recorded both events; the manifest folds them.
    ledger_file = tmp_path / ".skills-data" / "pipeline" / "ledger.jsonl"
    lines = [json.loads(line) for line in ledger_file.read_text().splitlines()]
    assert [e["action"] for e in lines] == ["REGISTER", "EXTRACT"]
    manifest = json.loads((tmp_path / ".skills-data" / "pipeline" / "manifest.json").read_text())
    assert manifest["documents"]["ddia_ch5"]["extracted"] is True


def test_register_is_not_repeatable(tmp_path: Path) -> None:
    src = _source(tmp_path)
    assert _run(REGISTER, src, root=tmp_path).returncode == 0
    dup = _run(REGISTER, src, root=tmp_path)
    assert dup.returncode == 1
    assert json.loads(dup.stderr)["error"] == "ALREADY_REGISTERED"


def test_extract_requires_registration(tmp_path: Path) -> None:
    src = _source(tmp_path)
    res = _run(EXTRACT, src, root=tmp_path)
    assert res.returncode == 1
    assert json.loads(res.stderr)["error"] == "NOT_REGISTERED"


def test_extract_is_not_repeatable(tmp_path: Path) -> None:
    src = _source(tmp_path)
    assert _run(REGISTER, src, root=tmp_path).returncode == 0
    assert _run(EXTRACT, src, root=tmp_path).returncode == 0
    dup = _run(EXTRACT, src, root=tmp_path)
    assert dup.returncode == 1
    assert json.loads(dup.stderr)["error"] == "ALREADY_EXTRACTED"


def test_extract_refuses_source_changed_after_registration(tmp_path: Path) -> None:
    src = _source(tmp_path)
    assert _run(REGISTER, src, root=tmp_path).returncode == 0
    src.write_text(CHAPTER + "\ntampered\n", encoding="utf-8")
    res = _run(EXTRACT, src, root=tmp_path)
    assert res.returncode == 1
    assert json.loads(res.stderr)["error"] == "SOURCE_CHANGED"


def test_non_markdown_source_refused(tmp_path: Path) -> None:
    pdf = tmp_path / "works" / "sources" / "book.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF-1.4 fake")
    res = _run(REGISTER, pdf, root=tmp_path)
    assert res.returncode == 1
    assert json.loads(res.stderr)["error"] == "UNSUPPORTED_FORMAT"


def test_status_reports_extraction_progress(tmp_path: Path) -> None:
    src = _source(tmp_path)
    _run(REGISTER, src, root=tmp_path)

    before = _run(STATUS, "--json", root=tmp_path)
    assert before.returncode == 0
    assert json.loads(before.stdout)["documents_extracted"] == 0

    _run(EXTRACT, src, root=tmp_path)
    after = _run(STATUS, "--json", root=tmp_path)
    parsed = json.loads(after.stdout)
    assert parsed["documents_extracted"] == 1 and parsed["documents_total"] == 1

    human = _run(STATUS, root=tmp_path)
    assert "documents extracted: 1/1" in human.stdout
