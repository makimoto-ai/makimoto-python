from __future__ import annotations

import logging

import httpx
import httpx2
import pytest

from makimoto.kawa import KawaClient, KawaError, KawaValidationError

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


# -- list_transcriptions ------------------------------------------------------------- #


def test_list_transcriptions_success(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(
            200, json={"transcriptions": [{"job_id": "abc", "status": "succeeded"}]}
        )
    )
    page = make_client().list_transcriptions()
    assert len(page.transcriptions) == 1
    assert page.transcriptions[0].job_id == "abc"
    assert page.transcriptions[0].status == "succeeded"
    assert page.next_cursor is None


def test_list_transcriptions_captures_all_list_only_fields(httpx2_mock):
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
                        "created_at": "2026-08-26T02:17:38.908Z",
                        "updated_at": "2026-08-26T02:17:40.398Z",
                    }
                ]
            },
        )
    )
    job = make_client().list_transcriptions().transcriptions[0]
    assert job.original_filename == "jackhammer.wav"
    assert job.language == "es"
    assert job.created_at == "2026-08-26T02:17:38.908Z"
    assert job.updated_at == "2026-08-26T02:17:40.398Z"


def test_list_transcriptions_exposes_next_cursor(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(
            200,
            json={
                "transcriptions": [{"job_id": "abc", "status": "succeeded"}],
                "next_cursor": "opaque-cursor-value",
            },
        )
    )
    page = make_client().list_transcriptions()
    assert page.next_cursor == "opaque-cursor-value"


def test_list_transcriptions_sends_pagination_and_filters(httpx2_mock):
    route = httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"transcriptions": []})
    )
    make_client().list_transcriptions(
        limit=5,
        cursor="prev-cursor",
        status="succeeded",
        language="en",
        created_after="2026-01-01T00:00:00Z",
        job_id="11111111-1111-1111-1111-111111111111",
    )
    sent = route.calls.last.request.url.params
    assert sent["limit"] == "5"
    assert sent["cursor"] == "prev-cursor"
    assert sent["status"] == "succeeded"
    assert sent["language"] == "en"
    assert sent["created_after"] == "2026-01-01T00:00:00Z"
    assert sent["job_id"] == "11111111-1111-1111-1111-111111111111"


def test_list_transcriptions_omits_unset_params(httpx2_mock):
    # None-valued args must not become literal "None" query params.
    route = httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"transcriptions": []})
    )
    make_client().list_transcriptions()
    assert dict(route.calls.last.request.url.params) == {}


# -- get_transcription --------------------------------------------------------------- #


def test_get_transcription_success(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(
            200,
            json={
                "job_id": "abc",
                "status": "succeeded",
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
    job = make_client().get_transcription("abc")
    assert job.is_terminal
    assert job.result is not None
    assert job.result.full_text == "hello world"


def test_kawa_validation_error_is_a_kawa_error():
    # Direct, no-HTTP-needed check of the class relationship itself, so this
    # guarantee doesn't rest on inference from a single mocked scenario.
    assert issubclass(KawaValidationError, KawaError)


def test_get_transcription_raises_on_malformed_response(httpx2_mock):
    # No job_id at all: a clear validation error, not a silently broken Job.
    # KawaValidationError is a KawaError, so `except KawaError` catches this too.
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(200, json={"status": "succeeded"})
    )
    with pytest.raises(KawaValidationError):
        make_client().get_transcription("abc")
    with pytest.raises(KawaError):
        make_client().get_transcription("abc")


def test_get_transcription_ignores_unknown_response_fields(httpx2_mock):
    # A future backend field shouldn't break an older SDK version.
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(
            200,
            json={"job_id": "abc", "status": "queued", "some_future_field": "ignored"},
        )
    )
    job = make_client().get_transcription("abc")
    assert job.job_id == "abc"


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


# -- delete_transcription ------------------------------------------------------------ #


def test_delete_transcription_success(httpx2_mock):
    httpx2_mock.delete(f"{BASE_URL}/v1/transcriptions/abc").mock(
        return_value=httpx.Response(202, json={})
    )
    result = make_client().delete_transcription("abc")
    assert result == {}


# -- error handling ------------------------------------------------------------------ #


def test_error_response_raises_kawa_error(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/missing").mock(
        return_value=httpx.Response(
            404, json={"error": {"code": "JOB_NOT_FOUND", "message": "Job not found"}}
        )
    )
    with pytest.raises(KawaError) as exc_info:
        make_client().get_transcription("missing")
    assert exc_info.value.status_code == 404
    assert "Job not found" in str(exc_info.value)


def test_non_json_error_body_does_not_crash(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions/broken").mock(
        return_value=httpx.Response(
            500, content=b"<html>not json</html>", headers={"content-type": "text/html"}
        )
    )
    with pytest.raises(KawaError) as exc_info:
        make_client().get_transcription("broken")
    assert exc_info.value.status_code == 500


def test_connection_error_raises_httpx2_connect_error(httpx2_mock):
    httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        side_effect=httpx2.ConnectError("boom")
    )
    with pytest.raises(httpx2.ConnectError):
        make_client().list_transcriptions()


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
    page = make_client().list_transcriptions()
    assert page.transcriptions == []


def test_sends_correct_auth_header(httpx2_mock):
    route = httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"transcriptions": []})
    )
    make_client(api_key="secret-key").list_transcriptions()
    assert route.calls.last.request.headers["authorization"] == "Bearer secret-key"


def test_headers_raises_when_api_key_empty(monkeypatch):
    # An explicit empty string must raise, not silently fall back to
    # whatever MAKIMOTO_API_KEY happens to be set to on the host.
    monkeypatch.delenv("MAKIMOTO_API_KEY", raising=False)
    with pytest.raises(ValueError):
        make_client(api_key="").list_transcriptions()


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
    assert result.result is not None
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
    # A failed job is a normal outcome, not a malfunction, matches get_transcription().
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
    KawaClient(api_key="explicit-key", api_url=BASE_URL).list_transcriptions()
    assert route.calls.last.request.headers["authorization"] == "Bearer explicit-key"


def test_falls_back_to_env_var(monkeypatch, httpx2_mock):
    monkeypatch.setenv("MAKIMOTO_API_KEY", "env-key")
    route = httpx2_mock.get(f"{BASE_URL}/v1/transcriptions").mock(
        return_value=httpx.Response(200, json={"transcriptions": []})
    )
    KawaClient(api_url=BASE_URL).list_transcriptions()
    assert route.calls.last.request.headers["authorization"] == "Bearer env-key"


def test_raises_when_no_credential_available(monkeypatch):
    monkeypatch.delenv("MAKIMOTO_API_KEY", raising=False)
    client = KawaClient(api_url=BASE_URL)
    with pytest.raises(ValueError):
        client.list_transcriptions()
