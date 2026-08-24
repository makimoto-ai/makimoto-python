# Changelog

All notable changes to `makimoto-kawa` are documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

<!-- version list -->

## v0.1.0 (2026-08-24)

- Initial Release

## 0.1.0 - 2026-08-27

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
