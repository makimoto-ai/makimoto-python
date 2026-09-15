"""Integration tests against a real, deployed makimoto-api (staging).

Unlike tests/test_kawa.py (fully mocked, no network), these hit a real
backend. They need STAGING_API_URL and STAGING_API_KEY set in the
environment, and skip themselves (not fail) when those aren't present, so a
plain `pytest` run without staging credentials configured stays green.

Run explicitly with `pytest -m integration` once both are set. See
CONTRIBUTING.md for how to obtain a staging API key and URL.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from makimoto.kawa import KawaClient, KawaError

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (os.environ.get("STAGING_API_URL") and os.environ.get("STAGING_API_KEY")),
        reason="STAGING_API_URL/STAGING_API_KEY not set",
    ),
]

# The same sample audio examples/quickstart.py ships with, see
# examples/audio/ATTRIBUTION.md for its source and licence terms.
_REPO_ROOT = Path(__file__).parent.parent.parent
SAMPLE_AUDIO = _REPO_ROOT / "examples" / "audio" / "jackhammer.wav"


@pytest.fixture
def staging_client():
    with KawaClient(
        api_key=os.environ["STAGING_API_KEY"],
        api_url=os.environ["STAGING_API_URL"],
    ) as client:
        yield client


def test_list_jobs_against_real_staging(staging_client):
    # A real contract check: confirms the response actually still matches
    # what TranscriptionPage expects, not just what the mocks assume it does.
    page = staging_client.list_jobs(limit=5)
    assert isinstance(page.transcriptions, list)
    assert page.next_cursor is None or isinstance(page.next_cursor, str)


def test_list_jobs_rejects_invalid_status(staging_client):
    # Confirms the backend still 400s on an unrecognised status rather than
    # silently ignoring it, and that this client surfaces that as KawaError.
    with pytest.raises(KawaError) as exc_info:
        staging_client.list_jobs(status="not-a-real-status")
    assert exc_info.value.status_code == 400


def test_create_and_poll_transcription_against_real_staging(staging_client):
    job = staging_client.transcribe(SAMPLE_AUDIO, language="en")
    assert job.status in ("succeeded", "failed")
    if job.status == "succeeded":
        assert job.result is not None
        assert job.result.full_text
