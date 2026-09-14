# Contributing

## Setup

```bash
git clone https://github.com/makimoto-ai/makimoto-python
cd makimoto-python
pip install -e ".[dev]"
pre-commit install --hook-type commit-msg --hook-type pre-commit
```

The `pre-commit` hooks enforce the commit message format below and run `ruff` locally, before you push.

## Running checks

```bash
ruff check .
ruff format --check .
pyrefly check
pytest --cov=makimoto --cov-report=term-missing
```

All of these also run in CI across Python 3.10, 3.11, and 3.12 on every pull request.

## Commit messages

Commits must follow [Conventional Commits](https://www.conventionalcommits.org/): `type: description`, using one of `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

This drives automated versioning: `feat` bumps the minor version, `fix` bumps the patch version, everything else (`chore`, `ci`, `docs`, etc.) doesn't trigger a release at all. Use `fix`/`feat` only for changes to the actual package under `src/makimoto`, use `chore`/`ci`/`docs` for tooling, workflows, and documentation changes.

## Pull requests

Branch off `main`, open a PR against it. CI (lint, format, type check, tests) and commit-lint both run automatically and must pass before merging.

## Releasing

Releases are PR-based, nothing ever pushes straight to `main`. On every push to `main`, `.github/workflows/release.yml` computes the next version from Conventional Commits and, if one is due, opens or updates a `chore/release` PR with the version bump and `CHANGELOG.md` entry. Merging that PR (through the same review and CI as any other PR) triggers a second job that tags the commit and creates the GitHub release, which in turn publishes to TestPyPI automatically. Publishing to the real PyPI stays a separate, manual step (`publish.yml`, `workflow_dispatch` only).

This depends on a repo secret, `RELEASE_PR_TOKEN`: a PAT (fine-grained, scoped to this repo, `contents: write` + `pull requests: write`) from an account with write access. This is required, not optional: GitHub refuses to let a PR opened with the default `GITHUB_TOKEN` trigger other workflows, so without this token the release PR's own required CI checks would never run and it could never be merged. Create it under the token-owning account's Settings → Developer settings → Fine-grained tokens, then add it as `RELEASE_PR_TOKEN` under this repo's Settings → Secrets and variables → Actions.
