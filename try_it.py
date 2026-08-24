"""Manual, real-API smoke test for the makimoto SDK, run as a developer would.

Not a unit test, not collected by pytest. Exercises the actual installed
package against the real production API.

    $env:MAKIMOTO_API_TOKEN = "<your real token>"     # PowerShell
    ./.venv/Scripts/python try_it.py
"""

from __future__ import annotations

import os
import sys

from makimoto.kawa import KawaClient, KawaError

DEFAULT_AUDIO = r"C:\repo\kawa\samples-audio\jackhammer.wav"


def main() -> int:
    token = os.getenv("MAKIMOTO_API_TOKEN", "").strip()
    if not token:
        print("Set MAKIMOTO_API_TOKEN first.")
        return 1

    audio = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_AUDIO
    client = KawaClient(token=token, api_url="https://api.makimoto.ai")

    try:
        job = client.create_transcription(audio, language="en")
        print(f"submitted {audio} -> job {job.job_id}")

        final = job
        for update in client.poll(job.job_id):
            print(f"  status: {update.status}")
            final = update
    except KawaError as exc:
        print(f"API error {exc.status_code}: {exc}")
        print(f"  body: {exc.body}")
        return 1

    if final.status != "succeeded" or not final.result:
        print(f"job did not succeed (status: {final.status}), error: {final.error}")
        return 1

    print(f"\nlanguage: {final.result.language}   words: {final.result.words_count}\n")
    print(final.result.full_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
