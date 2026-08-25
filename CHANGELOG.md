# Changelog

All notable changes to `makimoto-kawa` are documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

<!-- version list -->

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
