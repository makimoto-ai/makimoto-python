# Changelog

All notable changes to `makimoto-kawa` are documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

<!-- version list -->

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
