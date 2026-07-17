"""sys.path + root resolution for bare skill-script invocation.

Skill scripts are run as ``python3 skills/<skill>/scripts/<script>.py`` — no
package install, no pytest pythonpath. This module (imported first, for its
side effect) makes ``core/`` and ``schemas/`` importable.

Two distinct roots:

- **code root** — where ``core/`` and ``schemas/`` live: located by walking up
  from this file to ``pyproject.toml``. Never overridable.
- **data root** — where ``.skills-data/`` lives: defaults to the code root;
  ``FOUNDRY_ROOT`` overrides it (tests point it at a temp directory).
"""

import os
import sys
from pathlib import Path


def code_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError("pyproject.toml not found above this skill script")


def data_root() -> Path:
    override = os.environ.get("FOUNDRY_ROOT")
    return Path(override).resolve() if override else code_root()


_root = code_root()
for _entry in (str(_root / "core"), str(_root / "schemas")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)
