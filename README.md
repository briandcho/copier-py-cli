# copier-py-cli

A [Copier](https://copier.readthedocs.io/) template for scaffolding a minimal Python CLI tool
project (argument parsing via `argparse`, `--version`/`-V`, `setuptools-scm` versioning, tox,
pre-commit, and GitHub Actions CI/release/dependency-update workflows).

## Usage

Generate a new project:

```sh
copier copy https://github.com/briandcho/copier-py-cli my-project
```

`copier copy` fetches this repo's *latest git tag* by default (not `main`'s HEAD). Releases are cut
automatically on every push to `main` by `.github/workflows/release.yml`, which tags the next
version from Conventional Commits (a no-op if there's nothing releasable) — see `CLAUDE.md` if
you're maintaining this repo.

You'll be asked for:

- `project_name` — kebab-case project/package name (e.g. `my-project`); also used to derive the
  Python module name (`my_project`)
- `description` — short project description, used in `pyproject.toml` and `README.md`
- `author_name` / `author_email` — used in `pyproject.toml` and `LICENSE`
- `include_dep_automation` — whether to include a scheduled workflow that opens PRs to keep
  dependencies and Actions pins current (default yes)

Before `tox` works in the generated project, run `git init` (setuptools-scm needs git metadata to
compute the version) — see the generated project's own README for details.
`requirements.txt`/`requirements-dev.txt` ship with the template already resolved, so no separate
`pip-compile` step is needed first.

The generated project looks like:

```
my-project/
├── .github/
│   ├── dependabot.yml           # only if include_dep_automation
│   └── workflows/
│       ├── auto-update-deps.yml # only if include_dep_automation
│       ├── ci.yml
│       └── release.yml
├── .gitignore
├── .pre-commit-config.yaml
├── LICENSE
├── my_project.py
├── pyproject.toml
├── README.md
├── requirements.txt
├── requirements-dev.txt
└── tests/
    ├── __init__.py
    └── my_project_test.py
```

## Repo layout

- `copier.yml` — the questions asked above, plus `_subdirectory: template` (so the generated
  project doesn't itself contain a nested `template/` folder).
- `template/` — the actual template payload. Files ending in `.jinja` are rendered with the
  answers above (and have the suffix stripped); everything else is copied byte-for-byte.
- Everything else at the repo root (`pyproject.toml`, `tests/`, `scripts/`,
  `.pre-commit-config.yaml`, `.github/`) is this repo's own dev tooling, used only to test that the
  template renders correctly and to keep it and generated projects' pins current — it is not part
  of what gets generated.

## Development

### Install pre-commit hooks (including commit message checks)

This repo enforces Conventional Commits via a `commit-msg` hook (Commitizen). Most checks run on every commit; `pip-audit` (a network-bound dependency vulnerability scan) and `checkov` (an IaC scanner) are deferred to `pre-push` so they don't slow down every commit.

Install hooks locally:

```sh
pre-commit install --hook-type pre-commit --hook-type pre-push --hook-type commit-msg
# optional: run all hooks (including pip-audit) against the repo once
pre-commit run --all-files --hook-stage pre-push
```

If you see a commit rejected, format your message using Conventional Commits, for example:

```text
feat: add new question to copier.yml
fix(template): correct scripts entry point
chore(deps): weekly dependency updates
```

You can also use Commitizen to guide you:

```sh
cz commit
# or without installing: pipx run commitizen commit
```

### Use tox for development

This project uses `tox` to run tests and checks consistently across environments.

- Run the generation tests (renders the template, checks substitutions, installs the generated
  project into a throwaway venv, and runs its own test suite):

```sh
tox -e py
```

- Run all pre-commit hooks (format, lint, type-check, security, etc.):

```sh
tox -e pre-commit
```

- Run the pre-push-only hooks too (`pip-audit`, `checkov`) by passing extra args through to
  `pre-commit run` after `--`:

```sh
tox -e pre-commit -- --hook-stage pre-push
```

- Update this repo's own pinned dependencies and pre-commit hooks (also refreshes
  `template/requirements*.txt.jinja` and `template/.pre-commit-config.yaml` via
  `scripts/sync_generated_deps.py` — see `.github/workflows/deps-update.yml`, which runs both on
  a weekly schedule):

```sh
tox -e update_deps
python scripts/sync_generated_deps.py
```
