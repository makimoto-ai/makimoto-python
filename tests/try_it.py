"""Manual, real-API smoke test for the makimoto SDK, run as a developer would.

Not a unit test, not collected by pytest. Exercises the actual installed
package against the real production API.

    $env:MAKIMOTO_API_TOKEN = "<your real token>"     # PowerShell
    ./.venv/Scripts/python tests/try_it.py

Set MAKIMOTO_DEBUG=1 to also see every HTTP request/response (from httpx2's
own logger) and the SDK's own logging (e.g. poll() giving up), for example:

    $env:MAKIMOTO_DEBUG = "1"
"""

from __future__ import annotations

import logging
import os
import sys

from makimoto.kawa import KawaClient, KawaError

DEFAULT_AUDIO = r"C:\repo\kawa\samples-audio\jackhammer.wav"

if os.getenv("MAKIMOTO_DEBUG"):
    logging.basicConfig(level=logging.DEBUG)


def main() -> int:
    token = os.getenv("MAKIMOTO_API_TOKEN", "").strip()
    if not token:
        print("Set MAKIMOTO_API_TOKEN first.")
        return 1

    audio = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_AUDIO

    # `with` closes the client's connections on the way out, same as calling
    # client.close() explicitly, matters more for a long-running app than a
    # short script like this, but this is also the intended usage pattern.
    with KawaClient(token=token, api_url="https://api.makimoto.ai") as client:
        # One call: submits, polls internally, raises on timeout. This is the
        # whole point of transcribe() over the old create_transcription()+poll()
        # two-step, no manual loop needed for the common case.
        try:
            result = client.transcribe(audio, language="en")
        except KawaError as exc:
            print(f"API error {exc.status_code}: {exc}")
            print(f"  body: {exc.body}")
            return 1
        except TimeoutError as exc:
            print(f"gave up waiting: {exc}")
            return 1

    if result.status != "succeeded" or not result.result:
        # A failed job isn't an exception, transcribe() returns it normally.
        print(f"job did not succeed (status: {result.status}), error: {result.error}")
        return 1

    print(f"\nlanguage: {result.result.language}   words: {result.result.words_count}\n")
    print(result.result.full_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
