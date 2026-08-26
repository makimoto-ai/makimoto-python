# Usage

This page shows a quick demonstration of how to make use of the SDK. 

```python
from makimoto import kawa

client = kawa.KawaClient(token="<dashboard-token>")   # or set MAKIMOTO_API_TOKEN instead

job = client.transcribe("call.mp3", language="en")

if job.status == "succeeded":
    print(job.result.full_text)
else:
    print(job.error)
```

See the [quickstart examples](https://github.com/makimoto-ai/makimoto-python/blob/main/examples/quickstart.py) for a complete, runnable script; it ships with a small sample audio file, so `python examples/quickstart.py` works out of the box once `MAKIMOTO_API_TOKEN` is set.

`transcribe()` submits the recording and polls until it's done in one call, raising `TimeoutError` if it never finishes. For manual control (e.g. streaming live status updates to a UI), the lower-level primitives are still there:

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

Every call raises `kawa.KawaError` on an API-level failure (bad status code, or a response that doesn't match the expected shape), and `kawa.TimeoutError`-compatible `TimeoutError` from `transcribe()` if a job never finishes in time. A failed transcription job (`status == "failed"`) is not an exception, it's a normal result: check `.status`/`.error` as shown above.

```python
try:
    job = client.transcribe("call.mp3")
except kawa.KawaError as exc:
    print(exc.status_code, exc.body)
```

## Logging

Quiet by default. To see what the SDK is doing (credential source, a poll that gave up), or the raw HTTP traffic underneath it:

```python
import logging
logging.basicConfig()  # attaches a handler so the lines below actually print somewhere
logging.getLogger("makimoto.kawa.client").setLevel(logging.DEBUG)  # this SDK's own events
logging.getLogger("httpx2").setLevel(logging.DEBUG)                 # every request/response
```

See the [SDK API Reference](api-reference.md) for the full set of methods and models.
