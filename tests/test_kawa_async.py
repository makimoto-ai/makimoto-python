from __future__ import annotations

import json
import logging

import httpx
import httpx2
import pytest

from makimoto.kawa import (
    AsyncKawaClient,
    KawaError,
    KawaValidationError,
    SummaryResult,
    TranscriptResult,
)

BASE_URL = "https://api.makimoto.ai"


def make_client(**kwargs) -> AsyncKawaClient:
    kwargs.setdefault("api_key", "test-key")
    kwargs.setdefault("api_url", BASE_URL)
    return AsyncKawaClient(**kwargs)


# -- logging: quiet by default, own logger/NullHandler, distinct from the sync
#    client's, propagation across sibling loggers doesn't happen on its own ------- #


def test_logger_has_a_null_handler():
    logger = logging.getLogger("makimoto.kawa.async_client")
    assert any(isinstance(h, logging.NullHandler) for h in logger.handlers)


# -- lifecycle: aclose() / async context manager ------------------------------------- #


async def test_aclose_closes_the_session():
    client = make_client()
    assert client._session.is_closed is False
    await client.aclose()
    assert client._session.is_closed is True


async def test_async_context_manager_closes_on_exit():
    async with make_client() as client:
        assert client._session.is_closed is False
    assert client._session.is_closed is True


# -- list_jobs ----------------------------------------------------------------------- #


async def test_list_jobs_success(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(
            200, json={"transcriptions": [{"job_id": "abc", "status": "succeeded"}]}
        )
    )
    page = await make_client().list_jobs()
    assert len(page.transcriptions) == 1
    assert page.transcriptions[0].job_id == "abc"
    assert page.next_cursor is None


async def test_list_jobs_sends_pagination_and_filters(httpx2_mock):
    route = httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"transcriptions": []})
    )
    await make_client().list_jobs(
        limit=5,
        cursor="prev-cursor",
        status="succeeded",
        job_type="summary",
        language="en",
        created_after="2026-01-01T00:00:00Z",
        job_id="11111111-1111-1111-1111-111111111111",
    )
    sent = route.calls.last.request.url.params
    assert sent["limit"] == "5"
    assert sent["cursor"] == "prev-cursor"
    assert sent["status"] == "succeeded"
    assert sent["type"] == "summary"
    assert sent["language"] == "en"
    assert sent["created_after"] == "2026-01-01T00:00:00Z"
    assert sent["job_id"] == "11111111-1111-1111-1111-111111111111"


async def test_list_jobs_omits_unset_params(httpx2_mock):
    route = httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"transcriptions": []})
    )
    await make_client().list_jobs()
    assert dict(route.calls.last.request.url.params) == {}


# -- iter_jobs ----------------------------------------------------------------------- #


async def test_iter_jobs_walks_every_page(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "transcriptions": [{"job_id": "a", "status": "succeeded"}],
                    "next_cursor": "page-2",
                },
            ),
            httpx.Response(
                200,
                json={
                    "transcriptions": [{"job_id": "b", "status": "succeeded"}],
                    "next_cursor": None,
                },
            ),
        ]
    )
    job_ids = [job.job_id async for job in make_client().iter_jobs()]
    assert job_ids == ["a", "b"]


async def test_iter_jobs_stops_when_first_page_has_no_cursor(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(
            200,
            json={"transcriptions": [{"job_id": "solo", "status": "succeeded"}]},
        )
    )
    job_ids = [job.job_id async for job in make_client().iter_jobs()]
    assert job_ids == ["solo"]


# -- create_transcription ------------------------------------------------------------ #


async def test_create_transcription_success(httpx2_mock, tmp_path):
    audio_file = tmp_path / "call.mp3"
    audio_file.write_bytes(b"fake audio bytes")

    httpx2_mock.post(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(
            202, json={"job_id": "new-job", "status": "processing"}
        )
    )
    job = await make_client().create_transcription(audio_file, language="en")
    assert job.job_id == "new-job"
    assert job.status == "processing"


async def test_create_transcription_actually_sends_language_and_metadata(
    httpx2_mock, tmp_path
):
    audio_file = tmp_path / "call.mp3"
    audio_file.write_bytes(b"fake audio bytes")

    route = httpx2_mock.post(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(
            202, json={"job_id": "new-job", "status": "processing"}
        )
    )
    await make_client().create_transcription(
        audio_file, language="en", metadata={"source": "test"}
    )

    sent = route.calls.last.request.content.decode()
    assert 'name="language"' in sent
    assert "\r\n\r\nen\r\n" in sent
    assert 'name="metadata"' in sent
    assert '{"source":"test"}' in sent


# -- get_job ------------------------------------------------------------------------- #


async def test_get_job_success(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(
            200,
            json={
                "job_id": "abc",
                "status": "succeeded",
                "type": "transcription",
                "result": {
                    "language": "en",
                    "duration_seconds": 12.0,
                    "words_count": 2,
                    "transcript": [
                        {
                            "text": "hello world",
                            "time_start": 0,
                            "time_end": 1,
                            "speaker_id": 0,
                            "speaker_alias": "A",
                        }
                    ],
                },
            },
        )
    )
    job = await make_client().get_job("abc")
    assert job.is_terminal
    assert isinstance(job.result, TranscriptResult)
    assert job.result.full_text == "hello world"


async def test_get_job_raises_on_malformed_response(httpx2_mock):
    # No job_id at all: a clear validation error, not a silently broken Job.
    # KawaValidationError is a KawaError, so `except KawaError` catches this too.
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(200, json={"status": "succeeded"})
    )
    with pytest.raises(KawaValidationError):
        await make_client().get_job("abc")
    with pytest.raises(KawaError):
        await make_client().get_job("abc")


# -- delete_job ---------------------------------------------------------------------- #


async def test_delete_job_success(httpx2_mock):
    httpx2_mock.delete(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(202, json={})
    )
    result = await make_client().delete_job("abc")
    assert result == {}


# -- create_summary / create_tags ---------------------------------------------------- #


async def test_create_summary_success(httpx2_mock):
    route = httpx2_mock.post(f"{BASE_URL}/v1/summarize").mock(
        return_value=httpx.Response(
            202, json={"job_id": "summary-1", "type": "summary", "status": "processing"}
        )
    )
    job = await make_client().create_summary("transcription-1")
    assert job.job_id == "summary-1"
    assert job.result is None
    assert json.loads(route.calls.last.request.content) == {
        "transcription_job_id": "transcription-1"
    }


async def test_create_tags_success(httpx2_mock):
    httpx2_mock.post(f"{BASE_URL}/v1/tag").mock(
        return_value=httpx.Response(
            202, json={"job_id": "tags-1", "type": "tags", "status": "processing"}
        )
    )
    job = await make_client().create_tags("transcription-1")
    assert job.job_id == "tags-1"
    assert job.type == "tags"


async def test_create_summary_from_transcript_text(httpx2_mock):
    route = httpx2_mock.post(f"{BASE_URL}/v1/summarize").mock(
        return_value=httpx.Response(
            202, json={"job_id": "summary-2", "type": "summary", "status": "processing"}
        )
    )
    job = await make_client().create_summary(
        transcript_text="the customer called about a billing issue"
    )
    assert job.job_id == "summary-2"
    assert json.loads(route.calls.last.request.content) == {
        "transcript_text": "the customer called about a billing issue"
    }


async def test_create_tags_from_transcript_text(httpx2_mock):
    route = httpx2_mock.post(f"{BASE_URL}/v1/tag").mock(
        return_value=httpx.Response(
            202, json={"job_id": "tags-2", "type": "tags", "status": "processing"}
        )
    )
    job = await make_client().create_tags(
        transcript_text="the customer called about a billing issue"
    )
    assert job.job_id == "tags-2"
    assert json.loads(route.calls.last.request.content) == {
        "transcript_text": "the customer called about a billing issue"
    }


async def test_create_summary_raises_when_no_source_given(httpx2_mock):
    # Neither argument given: the SDK doesn't pre-validate, the API's own 400
    # surfaces as a KawaError, same as any other business-rule rejection.
    httpx2_mock.post(f"{BASE_URL}/v1/summarize").mock(
        return_value=httpx.Response(
            400,
            json={
                "error": {
                    "code": "MISSING_TRANSCRIPT_SOURCE",
                    "message": "Provide exactly one of transcription_job_id or "
                    "transcript_text.",
                }
            },
        )
    )
    with pytest.raises(KawaError) as exc_info:
        await make_client().create_summary()
    assert exc_info.value.status_code == 400


# -- error handling ------------------------------------------------------------------ #


async def test_error_response_raises_kawa_error(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/missing").mock(
        return_value=httpx.Response(
            404, json={"error": {"code": "JOB_NOT_FOUND", "message": "Job not found"}}
        )
    )
    with pytest.raises(KawaError) as exc_info:
        await make_client().get_job("missing")
    assert exc_info.value.status_code == 404
    assert "Job not found" in str(exc_info.value)


async def test_non_json_error_body_does_not_crash(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/broken").mock(
        return_value=httpx.Response(
            500, content=b"<html>not json</html>", headers={"content-type": "text/html"}
        )
    )
    with pytest.raises(KawaError) as exc_info:
        await make_client().get_job("broken")
    assert exc_info.value.status_code == 500


async def test_connection_error_raises_httpx2_connect_error(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        side_effect=httpx2.ConnectError("boom")
    )
    with pytest.raises(httpx2.ConnectError):
        await make_client().list_jobs()


# -- transport behaviour (httpx2-specific) ------------------------------------------- #


async def test_sends_correct_auth_header(httpx2_mock):
    route = httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"transcriptions": []})
    )
    await make_client(api_key="secret-key").list_jobs()
    assert route.calls.last.request.headers["authorization"] == "Bearer secret-key"


async def test_headers_raises_when_api_key_empty(monkeypatch):
    # An explicit empty string must raise, not silently fall back to
    # whatever MAKIMOTO_API_KEY happens to be set to on the host.
    monkeypatch.delenv("MAKIMOTO_API_KEY", raising=False)
    with pytest.raises(ValueError):
        await make_client(api_key="").list_jobs()


# -- poll ---------------------------------------------------------------------------- #


async def test_poll_stops_on_terminal_status(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        side_effect=[
            httpx.Response(200, json={"job_id": "abc", "status": "processing"}),
            httpx.Response(200, json={"job_id": "abc", "status": "succeeded"}),
        ]
    )
    client = make_client()
    updates = [job async for job in client.poll("abc", interval=0, max_attempts=5)]
    assert [u.status for u in updates] == ["processing", "succeeded"]
    assert updates[-1].is_terminal


async def test_poll_stops_without_raising_when_never_terminal(httpx2_mock):
    # Documents today's known gap on purpose: poll() gives up silently, no exception.
    # transcribe() (below) exists specifically to fix this for the common case.
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(200, json={"job_id": "abc", "status": "processing"})
    )
    client = make_client()
    updates = [job async for job in client.poll("abc", interval=0, max_attempts=3)]
    assert len(updates) == 3
    assert not updates[-1].is_terminal


async def test_poll_logs_warning_when_giving_up(httpx2_mock, caplog):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(200, json={"job_id": "abc", "status": "processing"})
    )
    with caplog.at_level(logging.WARNING, logger="makimoto.kawa.async_client"):
        [job async for job in make_client().poll("abc", interval=0, max_attempts=3)]
    assert len(caplog.records) == 1
    assert "gave up" in caplog.records[0].message
    assert "abc" in caplog.records[0].message


# -- logging: credential source, never the value itself ------------------------------ #


async def test_logs_debug_when_falling_back_to_env_var(monkeypatch, caplog):
    monkeypatch.setenv("MAKIMOTO_API_KEY", "super-secret-value")
    with caplog.at_level(logging.DEBUG, logger="makimoto.kawa.async_client"):
        client = AsyncKawaClient(api_url=BASE_URL)
    assert any("MAKIMOTO_API_KEY" in r.message for r in caplog.records)
    # The actual credential must never appear in a log record, only the fact
    # that the fallback happened.
    assert not any("super-secret-value" in r.message for r in caplog.records)
    await client.aclose()


# -- transcribe ---------------------------------------------------------------------- #


async def test_transcribe_returns_result_on_success(httpx2_mock, tmp_path):
    audio_file = tmp_path / "call.mp3"
    audio_file.write_bytes(b"fake audio bytes")
    httpx2_mock.post(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(202, json={"job_id": "abc", "status": "processing"})
    )
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(
            200,
            json={
                "job_id": "abc",
                "status": "succeeded",
                "result": {
                    "language": "en",
                    "duration_seconds": 1.0,
                    "words_count": 2,
                    "transcript": [
                        {
                            "text": "hi there",
                            "time_start": 0,
                            "time_end": 1,
                            "speaker_id": 0,
                            "speaker_alias": "A",
                        }
                    ],
                },
            },
        )
    )
    result = await make_client().transcribe(audio_file, interval=0)
    assert result.status == "succeeded"
    assert isinstance(result.result, TranscriptResult)
    assert result.result.full_text == "hi there"


async def test_transcribe_raises_timeout_error_when_exhausted(httpx2_mock, tmp_path):
    audio_file = tmp_path / "call.mp3"
    audio_file.write_bytes(b"fake audio bytes")
    httpx2_mock.post(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(202, json={"job_id": "abc", "status": "processing"})
    )
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(200, json={"job_id": "abc", "status": "processing"})
    )
    with pytest.raises(TimeoutError):
        await make_client().transcribe(audio_file, interval=0, max_attempts=2)


async def test_transcribe_returns_failed_job_without_raising(httpx2_mock, tmp_path):
    # A failed job is a normal outcome, not a malfunction, matches get_job().
    audio_file = tmp_path / "call.mp3"
    audio_file.write_bytes(b"fake audio bytes")
    httpx2_mock.post(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(202, json={"job_id": "abc", "status": "processing"})
    )
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(
            200,
            json={
                "job_id": "abc",
                "status": "failed",
                "error": {"code": "bad_audio", "message": "nope"},
            },
        )
    )
    result = await make_client().transcribe(audio_file, interval=0)
    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "bad_audio"


# -- credentials: explicit api_key / env var fallback -------------------------------- #


async def test_explicit_api_key_beats_env_var(monkeypatch, httpx2_mock):
    monkeypatch.setenv("MAKIMOTO_API_KEY", "env-key")
    route = httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"transcriptions": []})
    )
    client = AsyncKawaClient(api_key="explicit-key", api_url=BASE_URL)
    await client.list_jobs()
    assert route.calls.last.request.headers["authorization"] == "Bearer explicit-key"
    await client.aclose()


async def test_raises_when_no_credential_available(monkeypatch):
    monkeypatch.delenv("MAKIMOTO_API_KEY", raising=False)
    client = AsyncKawaClient(api_url=BASE_URL)
    with pytest.raises(ValueError):
        await client.list_jobs()
    await client.aclose()


# -- summary result parsing (confirms the async path routes result models correctly) - #


async def test_get_summary_job_parses_summary_result(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/summary-1").mock(
        return_value=httpx.Response(
            200,
            json={
                "job_id": "summary-1",
                "type": "summary",
                "status": "succeeded",
                "result": {"topic": "Billing", "summary": "Customer was billed twice."},
            },
        )
    )
    job = await make_client().get_job("summary-1")
    assert isinstance(job.result, SummaryResult)
    assert job.result.topic == "Billing"
