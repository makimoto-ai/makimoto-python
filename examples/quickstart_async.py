"""Runnable async demo of the makimoto SDK against the real production API.

    export MAKIMOTO_API_KEY="<your real api key>"      # bash
    $env:MAKIMOTO_API_KEY = "<your real api key>"       # PowerShell
    python examples/quickstart_async.py                       # uses the bundled
                                                               # sample audio
    python examples/quickstart_async.py path/to/your/audio.wav # or your own file

Set MAKIMOTO_DEBUG=1 to also see every HTTP request/response (from httpx2's
own logger) and the SDK's own logging (e.g. poll() giving up), for example:

    $env:MAKIMOTO_DEBUG = "1"

See quickstart.py for the sync equivalent; the two are otherwise identical.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from makimoto.kawa import AsyncKawaClient, KawaError, TranscriptResult

# See audio/ATTRIBUTION.md for this file's source and licence terms.
DEFAULT_AUDIO = Path(__file__).parent / "audio" / "jackhammer.wav"

if os.getenv("MAKIMOTO_DEBUG"):
    logging.basicConfig(level=logging.DEBUG)


async def main() -> int:
    api_key = os.getenv("MAKIMOTO_API_KEY", "").strip()
    if not api_key:
        print("Set MAKIMOTO_API_KEY first.")
        return 1

    audio = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_AUDIO

    # `async with` closes the client's connections on the way out, same as
    # calling await client.aclose() explicitly, matters more for a
    # long-running app than a short script like this, but this is also the
    # intended usage pattern.
    async with AsyncKawaClient(
        api_key=api_key, api_url="https://api.makimoto.ai"
    ) as client:
        # One call: submits, polls internally, raises on timeout.
        try:
            result = await client.transcribe(audio, language="en")
        except KawaError as exc:
            print(f"API error {exc.status_code}: {exc}")
            print(f"  body: {exc.body}")
            return 1
        except TimeoutError as exc:
            print(f"gave up waiting: {exc}")
            return 1

    # transcribe() only ever produces a transcription job, so result.result is a
    # TranscriptResult once succeeded; the isinstance check narrows that for the
    # type checker (Job.result is also SummaryResult | TagsResult for other job
    # types) and doubles as the same "didn't succeed" guard as before.
    if result.status != "succeeded" or not isinstance(result.result, TranscriptResult):
        # A failed job isn't an exception, transcribe() returns it normally.
        print(f"job did not succeed (status: {result.status}), error: {result.error}")
        return 1

    print(
        f"\nlanguage: {result.result.language}   words: {result.result.words_count}\n"
    )
    print(result.result.full_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
