from __future__ import annotations

import json
import logging

import httpx
import httpx2
import pytest

from makimoto.kawa import (
    KawaClient,
    KawaError,
    KawaValidationError,
    SummaryResult,
    TagsResult,
    TranscriptResult,
)
from makimoto.kawa._base import MULTIPART_MAX_BYTES

BASE_URL = "https://api.makimoto.ai"


def make_client(**kwargs) -> KawaClient:
    kwargs.setdefault("api_key", "test-key")
    kwargs.setdefault("api_url", BASE_URL)
    return KawaClient(**kwargs)


# -- logging: quiet by default, an app that never configures logging shouldn't
#    see this library's records printed to stderr on its own -------------------- #


def test_logger_has_a_null_handler():
    logger = logging.getLogger("makimoto.kawa.client")
    assert any(isinstance(h, logging.NullHandler) for h in logger.handlers)


# -- lifecycle: close() / context manager -------------------------------------------- #


def test_close_closes_the_session():
    client = make_client()
    assert client._session.is_closed is False
    client.close()
    assert client._session.is_closed is True


def test_context_manager_closes_on_exit():
    with make_client() as client:
        assert client._session.is_closed is False
    assert client._session.is_closed is True


# -- list_jobs ------------------------------------------------------------- #


def test_list_jobs_success(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(
            200, json={"transcriptions": [{"job_id": "abc", "status": "succeeded"}]}
        )
    )
    page = make_client().list_jobs()
    assert len(page.transcriptions) == 1
    assert page.transcriptions[0].job_id == "abc"
    assert page.transcriptions[0].status == "succeeded"
    assert page.next_cursor is None


def test_list_jobs_captures_all_list_only_fields(httpx2_mock):
    # These fields (confirmed present in real API responses) were previously
    # silently dropped by pydantic since Job didn't declare them at all.
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(
            200,
            json={
                "transcriptions": [
                    {
                        "job_id": "abc",
                        "status": "succeeded",
                        "original_filename": "jackhammer.wav",
                        "language": "es",
                        "audio_seconds": 12.5,
                        "created_at": "2026-08-26T02:17:38.908Z",
                        "updated_at": "2026-08-26T02:17:40.398Z",
                    }
                ]
            },
        )
    )
    job = make_client().list_jobs().transcriptions[0]
    assert job.original_filename == "jackhammer.wav"
    assert job.language == "es"
    assert job.audio_seconds == 12.5
    assert job.created_at == "2026-08-26T02:17:38.908Z"
    assert job.updated_at == "2026-08-26T02:17:40.398Z"


def test_list_jobs_exposes_next_cursor(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(
            200,
            json={
                "transcriptions": [{"job_id": "abc", "status": "succeeded"}],
                "next_cursor": "opaque-cursor-value",
            },
        )
    )
    page = make_client().list_jobs()
    assert page.next_cursor == "opaque-cursor-value"


def test_list_jobs_sends_pagination_and_filters(httpx2_mock):
    route = httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"transcriptions": []})
    )
    make_client().list_jobs(
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


def test_list_jobs_filters_by_job_type(httpx2_mock):
    # job_type is sent to the API as `type`, its own query param name.
    route = httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(
            200, json={"transcriptions": [{"job_id": "s1", "type": "summary"}]}
        )
    )
    page = make_client().list_jobs(job_type="summary")
    assert route.calls.last.request.url.params["type"] == "summary"
    assert page.transcriptions[0].type == "summary"


def test_list_jobs_omits_unset_params(httpx2_mock):
    # None-valued args must not become literal "None" query params.
    route = httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"transcriptions": []})
    )
    make_client().list_jobs()
    assert dict(route.calls.last.request.url.params) == {}


# -- iter_jobs ------------------------------------------------------------- #


def test_iter_jobs_walks_every_page(httpx2_mock):
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
    job_ids = [job.job_id for job in make_client().iter_jobs()]
    assert job_ids == ["a", "b"]


def test_iter_jobs_stops_when_first_page_has_no_cursor(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(
            200,
            json={"transcriptions": [{"job_id": "solo", "status": "succeeded"}]},
        )
    )
    job_ids = [job.job_id for job in make_client().iter_jobs()]
    assert job_ids == ["solo"]


def test_iter_jobs_reuses_filters_and_page_size_on_every_page(httpx2_mock):
    route = httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        side_effect=[
            httpx.Response(
                200,
                json={"transcriptions": [{"job_id": "a"}], "next_cursor": "page-2"},
            ),
            httpx.Response(200, json={"transcriptions": [{"job_id": "b"}]}),
        ]
    )
    list(make_client().iter_jobs(page_size=1, status="succeeded"))
    assert len(route.calls) == 2
    first, second = (dict(call.request.url.params) for call in route.calls)
    assert first == {"limit": "1", "status": "succeeded"}
    assert second == {"limit": "1", "status": "succeeded", "cursor": "page-2"}


def test_iter_jobs_passes_job_type_filter_on_every_page(httpx2_mock):
    route = httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"transcriptions": [{"job_id": "a"}]})
    )
    list(make_client().iter_jobs(job_type="tags"))
    assert route.calls.last.request.url.params["type"] == "tags"


# -- get_job --------------------------------------------------------------- #


def test_get_job_success(httpx2_mock):
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
    job = make_client().get_job("abc")
    assert job.is_terminal
    assert job.type == "transcription"
    assert isinstance(job.result, TranscriptResult)
    assert job.result.full_text == "hello world"


def test_kawa_validation_error_is_a_kawa_error():
    # Direct, no-HTTP-needed check of the class relationship itself, so this
    # guarantee doesn't rest on inference from a single mocked scenario.
    assert issubclass(KawaValidationError, KawaError)


def test_get_job_raises_on_malformed_response(httpx2_mock):
    # No job_id at all: a clear validation error, not a silently broken Job.
    # KawaValidationError is a KawaError, so `except KawaError` catches this too.
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(200, json={"status": "succeeded"})
    )
    with pytest.raises(KawaValidationError):
        make_client().get_job("abc")
    with pytest.raises(KawaError):
        make_client().get_job("abc")


def test_get_job_ignores_unknown_response_fields(httpx2_mock):
    # A future backend field shouldn't break an older SDK version.
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(
            200,
            json={"job_id": "abc", "status": "queued", "some_future_field": "ignored"},
        )
    )
    job = make_client().get_job("abc")
    assert job.job_id == "abc"


def test_get_summary_job_parses_summary_result(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/summary-1").mock(
        return_value=httpx.Response(
            200,
            json={
                "job_id": "summary-1",
                "type": "summary",
                "status": "succeeded",
                "source_job_id": "transcription-1",
                "result": {
                    "topic": "Billing",
                    "summary": "Customer was billed twice.",
                    "meta_data": {"model": "summarize-v1"},
                },
            },
        )
    )
    job = make_client().get_job("summary-1")
    assert job.type == "summary"
    assert job.source_job_id == "transcription-1"
    assert isinstance(job.result, SummaryResult)
    assert job.result.topic == "Billing"
    assert job.result.summary == "Customer was billed twice."


def test_get_tags_job_parses_tags_result(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/tags-1").mock(
        return_value=httpx.Response(
            200,
            json={
                "job_id": "tags-1",
                "type": "tags",
                "status": "succeeded",
                "result": {
                    "tags": {"call_reason": ["billing_issue"]},
                    "meta_data": None,
                },
            },
        )
    )
    job = make_client().get_job("tags-1")
    assert job.type == "tags"
    assert isinstance(job.result, TagsResult)
    assert job.result.tags == {"call_reason": ["billing_issue"]}


def test_transcription_result_still_parses_without_a_type_field(httpx2_mock):
    # Backwards compatibility: a response predating the `type` field must
    # still be treated as a transcription, not misrouted to another shape.
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
    job = make_client().get_job("abc")
    assert job.type is None
    assert isinstance(job.result, TranscriptResult)
    assert job.result.full_text == "hi there"


# -- create_transcription ------------------------------------------------------------ #


def test_create_transcription_success(httpx2_mock, tmp_path):
    audio_file = tmp_path / "call.mp3"
    audio_file.write_bytes(b"fake audio bytes")

    httpx2_mock.post(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(
            202, json={"job_id": "new-job", "status": "processing"}
        )
    )
    job = make_client().create_transcription(audio_file, language="en")
    assert job.job_id == "new-job"
    assert job.status == "processing"


def test_create_transcription_captures_received_at(httpx2_mock, tmp_path):
    audio_file = tmp_path / "call.mp3"
    audio_file.write_bytes(b"fake audio bytes")

    httpx2_mock.post(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(
            202,
            json={
                "job_id": "new-job",
                "status": "processing",
                "received_at": "2026-06-11T19:13:22.366Z",
            },
        )
    )
    job = make_client().create_transcription(audio_file, language="en")
    assert job.received_at == "2026-06-11T19:13:22.366Z"


def test_create_transcription_actually_sends_language_and_metadata(
    httpx2_mock, tmp_path
):
    # The test above only checks the response is parsed correctly, it never
    # confirms language/metadata were in the outgoing request at all, this does.
    audio_file = tmp_path / "call.mp3"
    audio_file.write_bytes(b"fake audio bytes")

    route = httpx2_mock.post(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(
            202, json={"job_id": "new-job", "status": "processing"}
        )
    )
    make_client().create_transcription(
        audio_file, language="en", metadata={"source": "test"}
    )

    sent = route.calls.last.request.content.decode()
    assert 'name="language"' in sent
    assert "\r\n\r\nen\r\n" in sent
    assert 'name="metadata"' in sent
    assert '{"source":"test"}' in sent


# -- delete_job ------------------------------------------------------------ #


def test_delete_job_success(httpx2_mock):
    httpx2_mock.delete(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(202, json={})
    )
    result = make_client().delete_job("abc")
    assert result == {}


# -- create_summary / create_tags ------------------------------------------------ #


def test_create_summary_success(httpx2_mock):
    route = httpx2_mock.post(f"{BASE_URL}/v1/summarize").mock(
        return_value=httpx.Response(
            202, json={"job_id": "summary-1", "type": "summary", "status": "processing"}
        )
    )
    job = make_client().create_summary("transcription-1")
    assert job.job_id == "summary-1"
    assert job.type == "summary"
    assert job.status == "processing"
    assert json.loads(route.calls.last.request.content) == {
        "transcription_job_id": "transcription-1"
    }


def test_create_tags_success(httpx2_mock):
    httpx2_mock.post(f"{BASE_URL}/v1/tag").mock(
        return_value=httpx.Response(
            202, json={"job_id": "tags-1", "type": "tags", "status": "processing"}
        )
    )
    job = make_client().create_tags("transcription-1")
    assert job.job_id == "tags-1"
    assert job.type == "tags"
    assert job.status == "processing"


def test_create_summary_from_transcript_text(httpx2_mock):
    route = httpx2_mock.post(f"{BASE_URL}/v1/summarize").mock(
        return_value=httpx.Response(
            202, json={"job_id": "summary-2", "type": "summary", "status": "processing"}
        )
    )
    job = make_client().create_summary(
        transcript_text="the customer called about a billing issue"
    )
    assert job.job_id == "summary-2"
    assert json.loads(route.calls.last.request.content) == {
        "transcript_text": "the customer called about a billing issue"
    }


def test_create_tags_from_transcript_text(httpx2_mock):
    route = httpx2_mock.post(f"{BASE_URL}/v1/tag").mock(
        return_value=httpx.Response(
            202, json={"job_id": "tags-2", "type": "tags", "status": "processing"}
        )
    )
    job = make_client().create_tags(
        transcript_text="the customer called about a billing issue"
    )
    assert job.job_id == "tags-2"
    assert json.loads(route.calls.last.request.content) == {
        "transcript_text": "the customer called about a billing issue"
    }


def test_create_summary_raises_when_no_source_given(httpx2_mock):
    # Neither argument given: the SDK doesn't pre-validate, the API's own 400
    # (MISSING_TRANSCRIPT_SOURCE) surfaces as a KawaError, same as any other
    # business-rule rejection.
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
        make_client().create_summary()
    assert exc_info.value.status_code == 400


def test_create_summary_raises_when_both_sources_given(httpx2_mock):
    httpx2_mock.post(f"{BASE_URL}/v1/summarize").mock(
        return_value=httpx.Response(
            400,
            json={
                "error": {
                    "code": "MULTIPLE_TRANSCRIPT_SOURCES",
                    "message": "Provide exactly one of transcription_job_id or "
                    "transcript_text.",
                }
            },
        )
    )
    with pytest.raises(KawaError) as exc_info:
        make_client().create_summary("transcription-1", transcript_text="also this")
    assert exc_info.value.status_code == 400


# -- error handling ------------------------------------------------------------------ #


def test_error_response_raises_kawa_error(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/missing").mock(
        return_value=httpx.Response(
            404, json={"error": {"code": "JOB_NOT_FOUND", "message": "Job not found"}}
        )
    )
    with pytest.raises(KawaError) as exc_info:
        make_client().get_job("missing")
    assert exc_info.value.status_code == 404
    assert "Job not found" in str(exc_info.value)


def test_non_json_error_body_does_not_crash(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/broken").mock(
        return_value=httpx.Response(
            500, content=b"<html>not json</html>", headers={"content-type": "text/html"}
        )
    )
    with pytest.raises(KawaError) as exc_info:
        make_client().get_job("broken")
    assert exc_info.value.status_code == 500


def test_connection_error_raises_httpx2_connect_error(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        side_effect=httpx2.ConnectError("boom")
    )
    with pytest.raises(httpx2.ConnectError):
        make_client().list_jobs()


# -- transport behaviour (httpx2-specific) ------------------------------------------- #


def test_follows_redirects(httpx2_mock):
    # httpx2.Client defaults to follow_redirects=False; requests.Session followed by
    # default, this must be set explicitly to keep parity.
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(
            302, headers={"location": f"{BASE_URL}/v1/transcriptions/"}
        )
    )
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/").mock(
        return_value=httpx.Response(200, json={"transcriptions": []})
    )
    page = make_client().list_jobs()
    assert page.transcriptions == []


def test_sends_correct_auth_header(httpx2_mock):
    route = httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"transcriptions": []})
    )
    make_client(api_key="secret-key").list_jobs()
    assert route.calls.last.request.headers["authorization"] == "Bearer secret-key"


def test_headers_raises_when_api_key_empty(monkeypatch):
    # An explicit empty string must raise, not silently fall back to
    # whatever MAKIMOTO_API_KEY happens to be set to on the host.
    monkeypatch.delenv("MAKIMOTO_API_KEY", raising=False)
    with pytest.raises(ValueError):
        make_client(api_key="").list_jobs()


# -- poll ---------------------------------------------------------------------------- #


def test_poll_stops_on_terminal_status(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        side_effect=[
            httpx.Response(200, json={"job_id": "abc", "status": "processing"}),
            httpx.Response(200, json={"job_id": "abc", "status": "succeeded"}),
        ]
    )
    updates = list(make_client().poll("abc", interval=0, max_attempts=5))
    assert [u.status for u in updates] == ["processing", "succeeded"]
    assert updates[-1].is_terminal


def test_poll_stops_without_raising_when_never_terminal(httpx2_mock):
    # Documents today's known gap on purpose: poll() gives up silently, no exception.
    # transcribe() (below) exists specifically to fix this for the common case.
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(200, json={"job_id": "abc", "status": "processing"})
    )
    updates = list(make_client().poll("abc", interval=0, max_attempts=3))
    assert len(updates) == 3
    assert not updates[-1].is_terminal


def test_poll_logs_warning_when_giving_up(httpx2_mock, caplog):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(200, json={"job_id": "abc", "status": "processing"})
    )
    with caplog.at_level(logging.WARNING, logger="makimoto.kawa.client"):
        list(make_client().poll("abc", interval=0, max_attempts=3))
    assert len(caplog.records) == 1
    assert "gave up" in caplog.records[0].message
    assert "abc" in caplog.records[0].message


def test_poll_logs_nothing_when_it_succeeds(httpx2_mock, caplog):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(200, json={"job_id": "abc", "status": "succeeded"})
    )
    with caplog.at_level(logging.WARNING, logger="makimoto.kawa.client"):
        list(make_client().poll("abc", interval=0, max_attempts=3))
    assert len(caplog.records) == 0


# -- logging: credential source, never the value itself ------------------------------ #


def test_logs_debug_when_falling_back_to_env_var(monkeypatch, caplog):
    monkeypatch.setenv("MAKIMOTO_API_KEY", "super-secret-value")
    with caplog.at_level(logging.DEBUG, logger="makimoto.kawa.client"):
        KawaClient(api_url=BASE_URL)
    assert any("MAKIMOTO_API_KEY" in r.message for r in caplog.records)
    # The actual credential must never appear in a log record, only the fact
    # that the fallback happened.
    assert not any("super-secret-value" in r.message for r in caplog.records)


def test_logs_nothing_credential_related_when_api_key_given_explicitly(caplog):
    with caplog.at_level(logging.DEBUG, logger="makimoto.kawa.client"):
        KawaClient(api_key="explicit-key", api_url=BASE_URL)
    assert not any("MAKIMOTO_API_KEY" in r.message for r in caplog.records)


# -- transcribe ---------------------------------------------------------------------- #


def test_transcribe_returns_result_on_success(httpx2_mock, tmp_path):
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
    result = make_client().transcribe(audio_file, interval=0)
    assert result.status == "succeeded"
    assert isinstance(result.result, TranscriptResult)
    assert result.result.full_text == "hi there"


def test_transcribe_raises_timeout_error_when_exhausted(httpx2_mock, tmp_path):
    audio_file = tmp_path / "call.mp3"
    audio_file.write_bytes(b"fake audio bytes")
    httpx2_mock.post(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(202, json={"job_id": "abc", "status": "processing"})
    )
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(200, json={"job_id": "abc", "status": "processing"})
    )
    with pytest.raises(TimeoutError):
        make_client().transcribe(audio_file, interval=0, max_attempts=2)


def test_transcribe_returns_failed_job_without_raising(httpx2_mock, tmp_path):
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
    result = make_client().transcribe(audio_file, interval=0)
    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "bad_audio"


# -- credentials: explicit api_key / env var fallback -------------------------------- #


def test_explicit_api_key_beats_env_var(monkeypatch, httpx2_mock):
    monkeypatch.setenv("MAKIMOTO_API_KEY", "env-key")
    route = httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"transcriptions": []})
    )
    KawaClient(api_key="explicit-key", api_url=BASE_URL).list_jobs()
    assert route.calls.last.request.headers["authorization"] == "Bearer explicit-key"


def test_falls_back_to_env_var(monkeypatch, httpx2_mock):
    monkeypatch.setenv("MAKIMOTO_API_KEY", "env-key")
    route = httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"transcriptions": []})
    )
    KawaClient(api_url=BASE_URL).list_jobs()
    assert route.calls.last.request.headers["authorization"] == "Bearer env-key"


def test_raises_when_no_credential_available(monkeypatch):
    monkeypatch.delenv("MAKIMOTO_API_KEY", raising=False)
    client = KawaClient(api_url=BASE_URL)
    with pytest.raises(ValueError):
        client.list_jobs()


# -- create_transcription: files over 4 MB go through a presigned upload ------ #

UPLOAD = {
    "upload_id": "up-1",
    "upload": {
        "url": "https://storage.example.com/upload",
        "fields": {
            "key": "up-1.mp3",
            "Content-Type": "audio/mpeg",
            "Policy": "p",
        },
    },
    "expires_at": "2026-10-28T10:15:00.000Z",
    "max_bytes": 15728640,
}
STORAGE_URL = UPLOAD["upload"]["url"]
TOO_BIG = "Your proposed upload exceeds the maximum allowed size"


def audio_of_size(tmp_path, size, name="long.mp3"):
    audio_file = tmp_path / name
    audio_file.write_bytes(b"\0" * size)
    return audio_file


def mock_upload(httpx2_mock, storage_response=None):
    uploads = httpx2_mock.post(f"{BASE_URL}/v1/uploads").mock(
        return_value=httpx.Response(201, json=UPLOAD)
    )
    storage = httpx2_mock.post(STORAGE_URL).mock(
        return_value=storage_response or httpx.Response(204)
    )
    return uploads, storage


def test_create_transcription_uploads_a_large_file_to_storage(httpx2_mock, tmp_path):
    uploads, storage = mock_upload(httpx2_mock)
    create = httpx2_mock.post(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(202, json={"job_id": "new-job", "status": "queued"})
    )

    job = make_client().create_transcription(
        audio_of_size(tmp_path, MULTIPART_MAX_BYTES + 1),
        language=" en ",
        metadata={"source": "test"},
    )

    assert job.job_id == "new-job"
    assert json.loads(uploads.calls.last.request.content) == {
        "filename": "long.mp3",
        "content_type": "audio/mpeg",
    }
    assert storage.called
    assert json.loads(create.calls.last.request.content) == {
        "upload_id": "up-1",
        "language": "en",
        "metadata": {"source": "test"},
    }


def test_storage_gets_the_signed_fields_first_and_no_api_key(httpx2_mock, tmp_path):
    _, storage = mock_upload(httpx2_mock)
    httpx2_mock.post(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(202, json={"job_id": "new-job", "status": "queued"})
    )

    make_client().create_transcription(audio_of_size(tmp_path, MULTIPART_MAX_BYTES + 1))

    request = storage.calls.last.request
    assert "authorization" not in request.headers
    sent = request.content
    positions = [
        sent.index(f'name="{n}"'.encode())
        for n in ("key", "Content-Type", "Policy", "file")
    ]
    assert positions == sorted(positions)


def test_a_file_at_the_threshold_is_still_sent_directly(httpx2_mock, tmp_path):
    create = httpx2_mock.post(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(202, json={"job_id": "new-job", "status": "queued"})
    )

    make_client().create_transcription(audio_of_size(tmp_path, MULTIPART_MAX_BYTES))

    assert b'name="file"' in create.calls.last.request.content


def test_storage_refusal_raises_with_its_reason_and_creates_no_job(
    httpx2_mock, tmp_path
):
    refusal = httpx.Response(
        400,
        text=f"<Error><Code>EntityTooLarge</Code><Message>{TOO_BIG}</Message></Error>",
    )
    mock_upload(httpx2_mock, storage_response=refusal)

    with pytest.raises(KawaError) as exc_info:
        make_client().create_transcription(
            audio_of_size(tmp_path, MULTIPART_MAX_BYTES + 1)
        )

    assert exc_info.value.status_code == 400
    assert str(exc_info.value) == f"Upload to storage failed: {TOO_BIG}"
    assert exc_info.value.body["error"]["code"] == "EntityTooLarge"


def test_an_upload_the_api_refuses_never_reaches_storage(httpx2_mock, tmp_path):
    httpx2_mock.post(f"{BASE_URL}/v1/uploads").mock(
        return_value=httpx.Response(
            429,
            json={"error": {"code": "TOO_MANY_OPEN_UPLOADS", "message": "Too many."}},
        )
    )

    with pytest.raises(KawaError) as exc_info:
        make_client().create_transcription(
            audio_of_size(tmp_path, MULTIPART_MAX_BYTES + 1)
        )

    assert exc_info.value.status_code == 429


def test_storage_gets_no_session_default_headers(httpx2_mock, tmp_path):
    _, storage = mock_upload(httpx2_mock)
    httpx2_mock.post(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(202, json={"job_id": "new-job", "status": "queued"})
    )
    session = httpx2.Client(
        headers={"Authorization": "Bearer session-default", "X-Extra": "1"}
    )

    make_client(session=session).create_transcription(
        audio_of_size(tmp_path, MULTIPART_MAX_BYTES + 1)
    )

    headers = storage.calls.last.request.headers
    assert "authorization" not in headers
    assert "x-extra" not in headers


def test_file_part_has_the_signed_content_type(httpx2_mock, tmp_path):
    _, storage = mock_upload(httpx2_mock)
    httpx2_mock.post(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(202, json={"job_id": "new-job", "status": "queued"})
    )

    make_client().create_transcription(audio_of_size(tmp_path, MULTIPART_MAX_BYTES + 1))

    sent = storage.calls.last.request.content
    file_part = sent[sent.index(b'name="file"') :]
    assert b"Content-Type: audio/mpeg" in file_part[:200]


def test_a_file_over_the_upload_limit_is_refused_before_storage(httpx2_mock, tmp_path):
    small_limit = {**UPLOAD, "max_bytes": MULTIPART_MAX_BYTES + 1}
    httpx2_mock.post(f"{BASE_URL}/v1/uploads").mock(
        return_value=httpx.Response(201, json=small_limit)
    )

    with pytest.raises(ValueError, match=r"over the .*-byte upload limit"):
        make_client().create_transcription(
            audio_of_size(tmp_path, MULTIPART_MAX_BYTES + 2)
        )


def test_a_malformed_upload_response_raises_validation_error(httpx2_mock, tmp_path):
    httpx2_mock.post(f"{BASE_URL}/v1/uploads").mock(
        return_value=httpx.Response(201, json={"unexpected": True})
    )

    with pytest.raises(KawaValidationError):
        make_client().create_transcription(
            audio_of_size(tmp_path, MULTIPART_MAX_BYTES + 1)
        )


def test_storage_error_message_is_unescaped(httpx2_mock, tmp_path):
    refusal = httpx.Response(
        403, text="<Error><Code>AccessDenied</Code><Message>A &amp; B</Message></Error>"
    )
    mock_upload(httpx2_mock, storage_response=refusal)

    with pytest.raises(KawaError, match="Upload to storage failed: A & B"):
        make_client().create_transcription(
            audio_of_size(tmp_path, MULTIPART_MAX_BYTES + 1)
        )
