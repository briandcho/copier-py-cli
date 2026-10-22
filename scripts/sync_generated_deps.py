"""Regenerate template/requirements*.txt.jinja and template/.pre-commit-config.yaml.

Generated projects don't run `pip-compile` themselves (see README.md /
template/README.md.jinja) -- instead their requirements*.txt ship as real template payload,
kept fresh by running `tox -e update_deps` inside a throwaway project generated from this
checkout and copying the result back here. This is what `.github/workflows/deps-update.yml`
calls on a schedule.
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = REPO_ROOT / "template"

sys.path.insert(0, str(REPO_ROOT / "tests"))
from copier_py_cli_test import ANSWERS, generate


def _require(executable: str) -> str:
    path = shutil.which(executable)
    if path is None:
        raise FileNotFoundError(f"{executable} not found on PATH")
    return path


def generate_and_update(throwaway: Path) -> None:  # pragma: no cover
    """Render a throwaway project from this checkout and resolve its own pins."""
    if throwaway.exists():
        shutil.rmtree(throwaway)
    generate(throwaway)
    subprocess.run([_require("git"), "init"], cwd=throwaway, check=True)  # nosec B603
    subprocess.run(  # nosec B603
        [_require("tox"), "-e", "update_deps"], cwd=throwaway, check=True
    )


def sync_requirements(throwaway: Path, template_dir: Path, project_name: str) -> None:
    """Copy a resolved throwaway project's pins back into the template payload.

    pip-compile annotates resolved packages with `# via <project_name> (pyproject.toml)`;
    since template_dir's files are Jinja templates shared by every generated project, the
    throwaway project's literal dummy name is swapped back for the `{{ project_name }}`
    placeholder so the annotation renders correctly for whatever name a real project picks.
    """
    for name in ("requirements.txt", "requirements-dev.txt"):
        content = (throwaway / name).read_text()
        content = content.replace(project_name, "{{ project_name }}")
        (template_dir / f"{name}.jinja").write_text(content)

    shutil.copy(
        throwaway / ".pre-commit-config.yaml", template_dir / ".pre-commit-config.yaml"
    )


def main() -> None:  # pragma: no cover
    throwaway = Path(tempfile.gettempdir()) / "copier-py-cli-throwaway"
    generate_and_update(throwaway)
    sync_requirements(throwaway, TEMPLATE_DIR, ANSWERS["project_name"])


if __name__ == "__main__":  # pragma: no cover
    main()
