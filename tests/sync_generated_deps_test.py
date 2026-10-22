from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from sync_generated_deps import _require, sync_action_pins, sync_requirements


def test_require_returns_the_resolved_path_for_an_executable_on_path():
    assert _require("python3") == shutil.which("python3")


def test_require_raises_for_an_executable_not_on_path():
    with pytest.raises(FileNotFoundError, match="not-a-real-executable"):
        _require("not-a-real-executable")


def test_sync_requirements_replaces_project_name_and_copies_pre_commit_config(tmp_path):
    throwaway = tmp_path / "throwaway"
    throwaway.mkdir()
    template_dir = tmp_path / "template"
    template_dir.mkdir()

    (throwaway / "requirements.txt").write_text(
        "some-pkg==1.0.0\n    # via my-project (pyproject.toml)\n"
    )
    (throwaway / "requirements-dev.txt").write_text(
        "covdefaults==2.3.0\n    # via my-project (pyproject.toml)\n"
    )
    (throwaway / ".pre-commit-config.yaml").write_text("repos: []\n")

    sync_requirements(throwaway, template_dir, "my-project")

    requirements = (template_dir / "requirements.txt.jinja").read_text()
    assert "my-project" not in requirements
    assert "# via {{ project_name }} (pyproject.toml)" in requirements

    requirements_dev = (template_dir / "requirements-dev.txt.jinja").read_text()
    assert "my-project" not in requirements_dev
    assert "# via {{ project_name }} (pyproject.toml)" in requirements_dev

    assert (template_dir / ".pre-commit-config.yaml").read_text() == "repos: []\n"


def test_sync_requirements_is_a_no_op_when_project_name_does_not_appear(tmp_path):
    throwaway = tmp_path / "throwaway"
    throwaway.mkdir()
    template_dir = tmp_path / "template"
    template_dir.mkdir()

    (throwaway / "requirements.txt").write_text("some-pkg==1.0.0\n")
    (throwaway / "requirements-dev.txt").write_text("covdefaults==2.3.0\n")
    (throwaway / ".pre-commit-config.yaml").write_text("repos: []\n")

    sync_requirements(throwaway, template_dir, "my-project")

    assert (template_dir / "requirements.txt.jinja").read_text() == "some-pkg==1.0.0\n"
    assert (
        template_dir / "requirements-dev.txt.jinja"
    ).read_text() == "covdefaults==2.3.0\n"


def test_sync_action_pins_copies_root_refs_into_template_workflows(tmp_path):
    root_dir = tmp_path / "root"
    root_dir.mkdir()
    template_dir = tmp_path / "template"
    template_dir.mkdir()

    (root_dir / "ci.yml").write_text(
        "      - uses: actions/checkout@v7\n"
        "        uses: trufflesecurity/trufflehog@v3.99.3\n"
    )
    (template_dir / "ci.yml").write_text(
        "      - uses: actions/checkout@v4\n"
        "        uses: trufflesecurity/trufflehog@v3.97.9\n"
        "        uses: actions/upload-artifact@v4\n"
    )

    sync_action_pins(root_dir, template_dir)

    assert (template_dir / "ci.yml").read_text() == (
        "      - uses: actions/checkout@v7\n"
        "        uses: trufflesecurity/trufflehog@v3.99.3\n"
        "        uses: actions/upload-artifact@v4\n"
    )


def test_sync_action_pins_rejects_conflicting_root_refs(tmp_path):
    root_dir = tmp_path / "root"
    root_dir.mkdir()
    template_dir = tmp_path / "template"
    template_dir.mkdir()

    (root_dir / "ci.yml").write_text("      - uses: actions/checkout@v7\n")
    (root_dir / "release.yml").write_text("      - uses: actions/checkout@v6\n")
    (template_dir / "ci.yml").write_text("      - uses: actions/checkout@v4\n")

    with pytest.raises(ValueError, match="actions/checkout"):
        sync_action_pins(root_dir, template_dir)
