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

## Integration tests

`tests/test_kawa.py` is fully mocked, no network. `tests/integration/` is the opposite: it calls the real `makimoto-api` staging deployment (`TranscriptionStack-staging`, an isolated copy of prod in the same AWS account, safe to create real jobs against), to catch actual contract drift a mock can't. It's not run against production, staging exists specifically so that isn't necessary.

These tests skip themselves, rather than fail, unless `STAGING_API_URL` and `STAGING_API_KEY` are set, so a plain `pytest` locally or in normal PR CI stays green without them. To run them for real:

1. Get the staging API's URL. There's no CloudFront/custom domain on staging yet, so this is the raw API Gateway invoke URL from the `TranscriptionStack-staging` CloudFormation stack's outputs (`aws cloudformation describe-stacks --stack-name TranscriptionStack-staging`), ask whoever last deployed it if you don't have AWS access yourself. It can change if the stack is ever torn down and redeployed.
2. Get a staging API key. This means logging into staging's Cognito Hosted UI first (`makimoto-transcribe-staging.auth.<region>.amazoncognito.com`) to get a JWT, then calling `POST /v1/api-keys` with it, there's no key sitting around for this already.
3. Run `STAGING_API_URL=... STAGING_API_KEY=... pytest -m integration -v`.

In CI, `.github/workflows/integration.yml` runs these nightly plus on `workflow_dispatch`, using the same two values as repo secrets, `STAGING_API_URL`/`STAGING_API_KEY`. It's deliberately not part of the normal per-PR `ci.yml`: this suite depends on live network and a backend that can be mid-redeploy, unlike the fully mocked default suite, it will occasionally fail for reasons that have nothing to do with your change.

## Commit messages

Commits must follow [Conventional Commits](https://www.conventionalcommits.org/): `type: description`, using one of `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

This drives automated versioning: `feat` bumps the minor version, `fix` bumps the patch version, everything else (`chore`, `ci`, `docs`, etc.) doesn't trigger a release at all. Use `fix`/`feat` only for changes to the actual package under `src/makimoto`, use `chore`/`ci`/`docs` for tooling, workflows, and documentation changes.

## Pull requests

Branch off `main`, open a PR against it. CI (lint, format, type check, tests) and commit-lint both run automatically and must pass before merging.

## Releasing

Releases are PR-based, nothing ever pushes straight to `main`. On every push to `main`, `.github/workflows/release.yml` computes the next version from Conventional Commits and, if one is due, opens or updates a `chore/release` PR with the version bump and `CHANGELOG.md` entry. Merging that PR (through the same review and CI as any other PR) triggers a second job that tags the commit and creates the GitHub release, which in turn publishes to TestPyPI automatically. Publishing to the real PyPI stays a separate, manual step (`publish.yml`, `workflow_dispatch` only).

This depends on a repo secret, `RELEASE_PR_TOKEN`: a PAT (fine-grained, scoped to this repo, `contents: write` + `pull requests: write`) from an account with write access. This is required, not optional: GitHub refuses to let a PR opened with the default `GITHUB_TOKEN` trigger other workflows, so without this token the release PR's own required CI checks would never run and it could never be merged. Create it under the token-owning account's Settings → Developer settings → Fine-grained tokens, then add it as `RELEASE_PR_TOKEN` under this repo's Settings → Secrets and variables → Actions.
