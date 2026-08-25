# Contributing

## Setup

```bash
git clone https://github.com/makimoto-ai/makimoto-python
cd makimoto-python
pip install -e ".[dev]"
pre-commit install --hook-type commit-msg
```

The `pre-commit` step enforces the commit message format below locally, before you push.

## Running checks

```bash
pytest
mypy src/makimoto --strict
```

Both also run in CI across Python 3.10, 3.11, and 3.12 on every pull request.

## Commit messages

Commits must follow [Conventional Commits](https://www.conventionalcommits.org/): `type: description`, using one of `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

This drives automated versioning: `feat` bumps the minor version, `fix` bumps the patch version, everything else (`chore`, `ci`, `docs`, etc.) doesn't trigger a release at all. Use `fix`/`feat` only for changes to the actual package under `src/makimoto`, use `chore`/`ci`/`docs` for tooling, workflows, and documentation changes.

## Pull requests

Branch off `main`, open a PR against it. CI (tests + type check) and commit-lint both run automatically and must pass before merging.
