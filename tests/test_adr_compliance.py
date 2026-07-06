"""ADR-compliance guards — static checks that architectural rules still hold.

These tests enforce cross-file consistency promises made in the docs and ADRs, so a
future edit (human or agent) cannot silently violate them.
"""
import ast
import re
from pathlib import Path
from typing import get_args

from pydantic import BaseModel

import discoverer_schema
import pipeline_ledger
import review
import taxonomy
from support import CANONICAL_ORDER

REPO_ROOT = Path(__file__).resolve().parent.parent

SCHEMA_MODULES = [taxonomy, discoverer_schema, review, pipeline_ledger]

# ADR 003: Phase-1 extraction code must never import an LLM client.
FORBIDDEN_LLM_MODULES = {
    "openai", "anthropic", "litellm", "ollama", "google.generativeai",
    "google.genai", "groq", "mistralai", "cohere", "langchain", "langchain_core",
}


def test_every_model_forbids_extra_fields() -> None:
    """ADR 010 / AGENTS.md rule 9: every Pydantic model sets extra='forbid'."""
    offenders = []
    for module in SCHEMA_MODULES:
        for name, obj in vars(module).items():
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseModel)
                and obj is not BaseModel
                and obj.__module__ == module.__name__
            ):
                if obj.model_config.get("extra") != "forbid":
                    offenders.append(f"{module.__name__}.{name}")
    assert not offenders, f"models missing extra='forbid': {offenders}"


def _bold_list_entries(markdown_path: Path) -> list:
    """Extract bold names from a numbered markdown list, tolerating 'Name:' colons."""
    text = markdown_path.read_text(encoding="utf-8")
    entries = re.findall(r"^\d+\.\s+\*\*(.+?)\*\*", text, flags=re.MULTILINE)
    return [entry.rstrip(":") for entry in entries]


def test_docs_taxonomy_md_matches_schema_order() -> None:
    """ADR 007: docs/taxonomy.md numbering IS the canonical evaluation order."""
    assert _bold_list_entries(REPO_ROOT / "docs" / "taxonomy.md") == CANONICAL_ORDER


def test_foundry_md_matches_schema_order() -> None:
    """ADR 007: Foundry.md's taxonomy listing mirrors the canonical order."""
    assert _bold_list_entries(REPO_ROOT / "Foundry.md") == CANONICAL_ORDER


def test_schema_order_is_the_machine_source_of_truth() -> None:
    assert list(get_args(discoverer_schema.TaxonomyLevel)) == CANONICAL_ORDER


def test_no_llm_clients_in_extraction_code() -> None:
    """ADR 003: deterministic extraction — no generative AI imports in Phase-1 code.

    Passes trivially until extraction code exists; guards it forever after.
    """
    candidate_files = []
    for pattern in ("src/**/*extract*/**/*.py", "src/**/*extract*.py", ".forge/skills/*extract*/**/*.py"):
        candidate_files.extend(REPO_ROOT.glob(pattern))

    violations = []
    for path in candidate_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if any(name == bad or name.startswith(bad + ".") for bad in FORBIDDEN_LLM_MODULES):
                    violations.append(f"{path}: imports {name}")
    assert not violations, f"ADR 003 violations: {violations}"


def test_skills_data_is_gitignored() -> None:
    """ADR 013: runtime state must never be committed."""
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".skills-data/" in [line.strip() for line in gitignore]
