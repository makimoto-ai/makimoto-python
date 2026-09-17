# Changelog

All notable changes to `makimoto-kawa` are documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

<!-- version list -->

## v0.2.1 (2026-09-17)

### Bug Fixes

- Satisfy ruff lint in the 0.2.0 demo notebook
  ([#14](https://github.com/makimoto-ai/makimoto-python/pull/14),
  [`9be7f11`](https://github.com/makimoto-ai/makimoto-python/commit/9be7f11449be49349c273c31dd7b0346d78eb5fb))

### Chores

- Updated README.md - Makimoto Website GA4 Tracking
  ([#13](https://github.com/makimoto-ai/makimoto-python/pull/13),
  [`3068c6a`](https://github.com/makimoto-ai/makimoto-python/commit/3068c6a048b7ba1d85526b21074954a8aa11f69e))

### Documentation

- Add jupyter notebook for 0.2.0 ([#14](https://github.com/makimoto-ai/makimoto-python/pull/14),
  [`9be7f11`](https://github.com/makimoto-ai/makimoto-python/commit/9be7f11449be49349c273c31dd7b0346d78eb5fb))

- Fixed docstring indentation ([#12](https://github.com/makimoto-ai/makimoto-python/pull/12),
  [`192fbc7`](https://github.com/makimoto-ai/makimoto-python/commit/192fbc75c36ca8bbeff3955475450a27f86d9f05))


## v0.2.0 (2026-09-15)

### Bug Fixes

- Add type and audio_seconds to Job, silently dropped until now
  ([#8](https://github.com/makimoto-ai/makimoto-python/pull/8),
  [`8d10398`](https://github.com/makimoto-ai/makimoto-python/commit/8d10398fba1fbce13162297866e0e4048d4a68f8))

- CI changes ([#11](https://github.com/makimoto-ai/makimoto-python/pull/11),
  [`bd59260`](https://github.com/makimoto-ai/makimoto-python/commit/bd592608616e44cde382da50746f49a1ceb50793))

- Fix for ruff check ([#11](https://github.com/makimoto-ai/makimoto-python/pull/11),
  [`bd59260`](https://github.com/makimoto-ai/makimoto-python/commit/bd592608616e44cde382da50746f49a1ceb50793))

- Remove deprecated method ([#11](https://github.com/makimoto-ai/makimoto-python/pull/11),
  [`bd59260`](https://github.com/makimoto-ai/makimoto-python/commit/bd592608616e44cde382da50746f49a1ceb50793))

- Resolve merge conflicts ([#11](https://github.com/makimoto-ai/makimoto-python/pull/11),
  [`bd59260`](https://github.com/makimoto-ai/makimoto-python/commit/bd592608616e44cde382da50746f49a1ceb50793))

- Switch auth from JWT token to a static api_key
  ([#4](https://github.com/makimoto-ai/makimoto-python/pull/4),
  [`3a6cec4`](https://github.com/makimoto-ai/makimoto-python/commit/3a6cec4f2482687eb89fbe0b5d647bad01ffe948))

- Updated delete_transcription to delete_job
  ([#11](https://github.com/makimoto-ai/makimoto-python/pull/11),
  [`bd59260`](https://github.com/makimoto-ai/makimoto-python/commit/bd592608616e44cde382da50746f49a1ceb50793))

- Updated get-transcription to get-job
  ([#11](https://github.com/makimoto-ai/makimoto-python/pull/11),
  [`bd59260`](https://github.com/makimoto-ai/makimoto-python/commit/bd592608616e44cde382da50746f49a1ceb50793))

### Chores

- Updated init docstring ([#11](https://github.com/makimoto-ai/makimoto-python/pull/11),
  [`bd59260`](https://github.com/makimoto-ai/makimoto-python/commit/bd592608616e44cde382da50746f49a1ceb50793))

### Code Style

- Apply ruff formatting to source, examples, and docs
  ([#3](https://github.com/makimoto-ai/makimoto-python/pull/3),
  [`1ace21a`](https://github.com/makimoto-ai/makimoto-python/commit/1ace21aaa68fb06c0c464270415d0ef13ce8ccc5))

### Continuous Integration

- Compare against HEAD to detect a due release, not the index
  ([#9](https://github.com/makimoto-ai/makimoto-python/pull/9),
  [`ce08096`](https://github.com/makimoto-ai/makimoto-python/commit/ce080966d76643a355a51e132ad39e2695918686))

- Harden CI/CD with ruff, pyrefly, coverage gate, PR-based release
  ([#3](https://github.com/makimoto-ai/makimoto-python/pull/3),
  [`1ace21a`](https://github.com/makimoto-ai/makimoto-python/commit/1ace21aaa68fb06c0c464270415d0ef13ce8ccc5))

- Replace mypy with ruff + pyrefly, add coverage gate
  ([#3](https://github.com/makimoto-ai/makimoto-python/pull/3),
  [`1ace21a`](https://github.com/makimoto-ai/makimoto-python/commit/1ace21aaa68fb06c0c464270415d0ef13ce8ccc5))

- Switch release automation to a PR-based flow
  ([#3](https://github.com/makimoto-ai/makimoto-python/pull/3),
  [`1ace21a`](https://github.com/makimoto-ai/makimoto-python/commit/1ace21aaa68fb06c0c464270415d0ef13ce8ccc5))

### Documentation

- Add list_transcriptions()/iter_transcriptions() usage examples
  ([#5](https://github.com/makimoto-ai/makimoto-python/pull/5),
  [`2d5fd0b`](https://github.com/makimoto-ai/makimoto-python/commit/2d5fd0b3628fbf1081f07f141ba5f0a00e56a8d9))

- Updated docstrings for client ([#11](https://github.com/makimoto-ai/makimoto-python/pull/11),
  [`bd59260`](https://github.com/makimoto-ai/makimoto-python/commit/bd592608616e44cde382da50746f49a1ceb50793))

- Updated docstrings for exceptions ([#11](https://github.com/makimoto-ai/makimoto-python/pull/11),
  [`bd59260`](https://github.com/makimoto-ai/makimoto-python/commit/bd592608616e44cde382da50746f49a1ceb50793))

- Updated docstrings for models ([#11](https://github.com/makimoto-ai/makimoto-python/pull/11),
  [`bd59260`](https://github.com/makimoto-ai/makimoto-python/commit/bd592608616e44cde382da50746f49a1ceb50793))

### Features

- Add iter_transcriptions() to auto-paginate list_transcriptions()
  ([#5](https://github.com/makimoto-ai/makimoto-python/pull/5),
  [`2d5fd0b`](https://github.com/makimoto-ai/makimoto-python/commit/2d5fd0b3628fbf1081f07f141ba5f0a00e56a8d9))

- Add pagination and filters to list_transcriptions()
  ([#5](https://github.com/makimoto-ai/makimoto-python/pull/5),
  [`2d5fd0b`](https://github.com/makimoto-ai/makimoto-python/commit/2d5fd0b3628fbf1081f07f141ba5f0a00e56a8d9))

- Added models for transcript and summary results
  ([#11](https://github.com/makimoto-ai/makimoto-python/pull/11),
  [`bd59260`](https://github.com/makimoto-ai/makimoto-python/commit/bd592608616e44cde382da50746f49a1ceb50793))

- Added tag, summary methods ([#11](https://github.com/makimoto-ai/makimoto-python/pull/11),
  [`bd59260`](https://github.com/makimoto-ai/makimoto-python/commit/bd592608616e44cde382da50746f49a1ceb50793))

- Summarize tagging services ([#11](https://github.com/makimoto-ai/makimoto-python/pull/11),
  [`bd59260`](https://github.com/makimoto-ai/makimoto-python/commit/bd592608616e44cde382da50746f49a1ceb50793))

### Testing

- Add an integration suite against real staging
  ([#7](https://github.com/makimoto-ai/makimoto-python/pull/7),
  [`d9457fe`](https://github.com/makimoto-ai/makimoto-python/commit/d9457fec9f584eefc76376b5d2f1b691c075e84d))

- Narrow Optional access pyrefly caught, normalize dividers
  ([#3](https://github.com/makimoto-ai/makimoto-python/pull/3),
  [`1ace21a`](https://github.com/makimoto-ai/makimoto-python/commit/1ace21aaa68fb06c0c464270415d0ef13ce8ccc5))


## v0.1.3 (2026-08-27)


## v0.1.2 (2026-08-27)

### Bug Fixes

- Correct broken kawa API docs link in README
  ([`ce1b3a5`](https://github.com/makimoto-ai/makimoto-python/commit/ce1b3a5890b2e8c03a2e2476ff2714aac2d9a4f6))

### Chores

- Edited README and added new test
  ([`282a079`](https://github.com/makimoto-ai/makimoto-python/commit/282a0793466d9706d66993e67ef4791c62d21166))

- Fix release.yml + readme
  ([`f9c9843`](https://github.com/makimoto-ai/makimoto-python/commit/f9c9843b71944817a055cbe4b47322c91784ab4f))

### Documentation

- Cache-bust PyPI/Python version badges after first real publish
  ([`baffa20`](https://github.com/makimoto-ai/makimoto-python/commit/baffa20963d37b02752f995f87f5f06a7670f579))

- Create documentation
  ([`2bf9d36`](https://github.com/makimoto-ai/makimoto-python/commit/2bf9d36ceabd055bd21542c9a28263ced8b498df))

- Edit 'Licence' spelling to match kawa
  ([`b73b5d7`](https://github.com/makimoto-ai/makimoto-python/commit/b73b5d720e8314e6a74422b0e15b6496e4ff1151))

- Edit README
  ([`366da93`](https://github.com/makimoto-ai/makimoto-python/commit/366da935faa37366c7a1c9d660fc29e89ecd4443))

- Exit README to makimoto-kawa
  ([`e6bbd80`](https://github.com/makimoto-ai/makimoto-python/commit/e6bbd80785de315402cf977c9684dd34cc9ccdf5))


## v0.1.1 (2026-08-25)

### Bug Fixes

- Fixed publish workflows to testpypi and pypi
  ([`da4f631`](https://github.com/makimoto-ai/makimoto-python/commit/da4f6316db647576242be5314cfa0b3ec248dfbc))

### Chores

- Added publish workflow files to both testpypi and pypi
  ([`4002f14`](https://github.com/makimoto-ai/makimoto-python/commit/4002f1485c3829eec91fc551ee43399dfc6bf0e3))

- Remove stray root-level try_it.py
  ([`f51fc54`](https://github.com/makimoto-ai/makimoto-python/commit/f51fc54e9d9a63e1d9e92278d5f1892d0ba49372))

- Restore release.yml trigger, del dupe changelong entry
  ([`737676d`](https://github.com/makimoto-ai/makimoto-python/commit/737676d98f0fe87d5f3af07a041d8d7fec92addb))


## v0.1.0 (2026-08-24)

Initial release.

### Added
- `KawaClient`: `list_transcriptions()`, `create_transcription()`, `get_transcription()`, `delete_transcription()`, `usage()`, `poll()`.
- `transcribe()`: one-call submit-and-poll convenience. Raises `TimeoutError` if it never finishes; returns normally on a `failed` job, that's a normal outcome, not a malfunction.
- Credential handling: `token` argument, falling back to a `MAKIMOTO_API_TOKEN` environment variable when omitted.
- `close()` and context-manager support (`with KawaClient(...) as client:`), releases the underlying HTTP session's pooled connections.
- `KawaError` for HTTP-level failures, `KawaValidationError` (a `KawaError` subclass) for a 2xx response that doesn't match the expected shape, so `except KawaError` catches both.
- SDK-level logging under `makimoto.kawa.client` (credential source, `poll()` giving up), silent by default (`NullHandler`) unless a consumer configures it.
- Response models (`Job`, `Segment`, `TranscriptResult`, `JobError`, `Usage`) as `pydantic` models, replacing hand-written parsing.
- Full test suite (`pytest` + `pytest-httpx2`).
- MIT licensed.
