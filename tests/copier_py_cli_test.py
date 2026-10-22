from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

import copier

REPO_ROOT = Path(__file__).resolve().parent.parent

ANSWERS = {
    "project_name": "my-project",
    "description": "An example generated project",
    "author_name": "Jane Doe",
    "author_email": "jane@example.com",
}


def generate(dst: Path, **answer_overrides: object) -> None:
    # vcs_ref="HEAD" is required: copier defaults to the latest git tag for local git
    # sources, which would render an old, pre-template commit instead of this checkout
    # (including any uncommitted changes, since the source repo is dirty).
    copier.run_copy(
        str(REPO_ROOT),
        str(dst),
        data={**ANSWERS, **answer_overrides},
        defaults=True,
        overwrite=True,
        vcs_ref="HEAD",
    )


def test_generated_project_structure_and_substitutions(tmp_path):
    dst = tmp_path / "generated"
    generate(dst)

    module_path = dst / "my_project.py"
    test_path = dst / "tests" / "my_project_test.py"
    assert module_path.is_file()
    assert test_path.is_file()
    assert (dst / "tests" / "__init__.py").is_file()

    # No leftover unrendered template filenames anywhere in the output.
    leftover = [p for p in dst.rglob("*{{*")]
    assert leftover == []

    # .copier-answers.yml must be generated so `copier update` (used by
    # auto-update-deps.yml) has a source of truth for the template URL/version.
    answers = (dst / ".copier-answers.yml").read_text()
    assert "project_name: my-project" in answers
    assert "author_name: Jane Doe" in answers

    pyproject = (dst / "pyproject.toml").read_text()
    assert 'name = "my-project"' in pyproject
    assert 'description = "An example generated project"' in pyproject
    assert 'name = "Jane Doe", email = "jane@example.com"' in pyproject
    assert 'scripts.my-project = "my_project:main"' in pyproject
    assert 'license = "MIT"' in pyproject
    assert 'license-files = [ "LICENSE" ]' in pyproject

    readme = (dst / "README.md").read_text()
    assert readme.startswith("# my-project")
    assert "An example generated project" in readme
    assert "my-project --version" in readme

    license_text = (dst / "LICENSE").read_text()
    assert "Jane Doe" in license_text

    module_text = module_path.read_text()
    assert 'resolve_package_version("my-project")' in module_text

    test_text = test_path.read_text()
    assert "from my_project import __version__, main" in test_text

    for name in ("auto-update-deps.yml", "ci.yml", "release.yml"):
        workflow = dst / ".github" / "workflows" / name
        assert workflow.is_file()
        assert (
            "${{ github" in workflow.read_text()
            or "${{ secrets" in workflow.read_text()
        )

    assert (dst / ".github" / "dependabot.yml").is_file()

    requirements_dev = (dst / "requirements-dev.txt").read_text()
    assert "my-project" in requirements_dev


def test_include_dep_automation_false_omits_dependabot_and_auto_update_workflow(
    tmp_path,
):
    dst = tmp_path / "generated"
    generate(dst, include_dep_automation=False)

    assert not (dst / ".github" / "dependabot.yml").exists()
    assert not (dst / ".github" / "workflows" / "auto-update-deps.yml").exists()

    # Unrelated workflows and payload are unaffected.
    assert (dst / ".github" / "workflows" / "ci.yml").is_file()
    assert (dst / ".github" / "workflows" / "release.yml").is_file()
    assert (dst / "requirements-dev.txt").is_file()


def test_requirements_render_with_the_chosen_project_name(tmp_path):
    dst = tmp_path / "generated"
    generate(dst, project_name="widget-cli")

    requirements_dev = (dst / "requirements-dev.txt").read_text()
    assert "widget-cli" in requirements_dev
    assert "my-project" not in requirements_dev


def test_generated_project_installs_and_passes_its_own_tests(tmp_path):
    dst = tmp_path / "generated"
    generate(dst)

    venv_dir = tmp_path / "venv"
    venv.create(venv_dir, with_pip=True)
    bin_dir = "Scripts" if sys.platform == "win32" else "bin"
    exe = "python.exe" if sys.platform == "win32" else "python"
    venv_python = venv_dir / bin_dir / exe

    env = os.environ.copy()
    # The generated project has no git tags for setuptools-scm to resolve a version from.
    env["SETUPTOOLS_SCM_PRETEND_VERSION"] = "0.1.0"

    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-e", f"{dst}[dev]"],
        check=True,
        cwd=dst,
        env=env,
    )
    subprocess.run(
        [str(venv_python), "-m", "pytest"],
        check=True,
        cwd=dst,
        env=env,
    )
