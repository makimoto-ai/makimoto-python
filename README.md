# makimoto

Official Python SDK for the Makimoto transcription API.

## Install

Requires Python 3.10+.

```bash
pip install makimoto-kawa
```

## Authentication

Get a token from the Makimoto dashboard: <https://www.makimoto.ai/login>.

For now, this is a short-lived JWT, not a persistent API key, it expires, so copy a fresh one from the dashboard if requests start failing with `401`. This will change to a static API key in the near future; when it does, the same `token`/`MAKIMOTO_API_TOKEN` mechanism below will keep working, only what you paste in changes.

```python
client = kawa.KawaClient(token="<dashboard-token>")
```

or set it once as an environment variable and omit the argument entirely:

```bash
export MAKIMOTO_API_TOKEN="<dashboard-token>"
```

An explicit `token` argument always wins over the environment variable if both are set.

## Usage

```python
from makimoto import kawa

client = kawa.KawaClient(token="<dashboard-token>")   # or set MAKIMOTO_API_TOKEN instead

job = client.transcribe("call.mp3", language="en")

if job.status == "succeeded":
    print(job.result.full_text)
else:
    print(job.error)
```

`transcribe()` submits the recording and polls until it's done in one call, raising `TimeoutError` if it never finishes. For manual control, e.g. streaming live status updates to a UI, the lower-level primitives are still there:

```python
job = client.create_transcription("call.mp3", language="en")

for update in client.poll(job.job_id):
    print(update.status)
```

Check your account's transcription quota:

```python
usage = client.usage()
print(f"{usage.used_minutes}/{usage.limit_minutes} minutes used")
```

Release the client's connections when you're done with it, or use it as a context manager:

```python
with kawa.KawaClient(token="<dashboard-token>") as client:
    ...
```

## Errors

Every call raises `kawa.KawaError` on an API-level failure (bad status code, or a response that doesn't match the expected shape), and `kawa.TimeoutError`-compatible `TimeoutError` from `transcribe()` if a job never finishes in time. A failed transcription job (`status == "failed"`) is not an exception, it's a normal result, check `.status`/`.error` as shown above.

```python
from makimoto.kawa import KawaError

try:
    job = client.transcribe("call.mp3")
except KawaError as exc:
    print(exc.status_code, exc.body)
```

## Logging

Quiet by default. To see what the SDK is doing (credential source, a poll that gave up), or the raw HTTP traffic underneath it:

```python
import logging
logging.getLogger("makimoto.kawa.client").setLevel(logging.DEBUG)  # this SDK's own events
logging.getLogger("httpx2").setLevel(logging.DEBUG)                 # every request/response
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

[MIT](LICENSE)
