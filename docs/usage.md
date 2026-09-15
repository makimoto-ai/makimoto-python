# Usage

*Last updated: 2026-09-15*

This page shows a quick demonstration of how to make use of the SDK. 

```python
from makimoto import kawa

client = kawa.KawaClient(api_key="<your api key>")  # or set MAKIMOTO_API_KEY instead

job = client.transcribe("call.mp3", language="en")

if job.status == "succeeded":
    print(job.result.full_text)
else:
    print(job.error)
```

See the [quickstart examples](https://github.com/makimoto-ai/makimoto-python/blob/main/examples/quickstart.py) for a complete, runnable script; it ships with a small sample audio file, so `python examples/quickstart.py` works out of the box once `MAKIMOTO_API_KEY` is set.

`transcribe()` submits the recording and polls until it's done in one call, raising `TimeoutError` if it never finishes. For manual control (e.g. streaming live status updates to a UI), the lower-level primitives are still there:

```python
job = client.create_transcription("call.mp3", language="en")

for update in client.poll(job.job_id):
    print(update.status)
```

Once a transcription has succeeded, summarise or tag it by its `job_id`. Both return a new job, fetched or polled the same way as a transcription, through its own `job_id`, not the source transcription's:

```python
summary_job = client.create_summary(job.job_id)
for update in client.poll(summary_job.job_id):
    print(update.status)
print(update.result.topic, update.result.summary)

tags_job = client.create_tags(job.job_id)
for update in client.poll(tags_job.job_id):
    print(update.status)
print(update.result.tags)
```

Or skip the transcription entirely and summarise/tag a transcript you already have, with `transcript_text` instead of a job id (exactly one of the two must be given):

```python
summary_job = client.create_summary(
    transcript_text="the customer called about a billing issue..."
)
```

Also fetch or delete any job (transcription, summary, or tags) directly by its `job_id`:

```python
job = client.get_job(job.job_id)
client.delete_job(job.job_id)
```

List past jobs, one page at a time, with optional filters (`status`, `job_type`, `language`, `created_after`, `job_id`). With no `job_type`, every job type (transcription, summary, and tags) is returned:

```python
page = client.list_jobs(job_type="summary", status="succeeded", limit=25)
for job in page.transcriptions:
    print(job.job_id, job.status)

if page.next_cursor:
    next_page = client.list_jobs(cursor=page.next_cursor)
```

Or walk every matching job across all pages automatically:

```python
for job in client.iter_jobs(job_type="tags", status="succeeded"):
    print(job.job_id)
```

Release the client's connections when you're done with it, or use it as a context manager:

```python
with kawa.KawaClient(api_key="<your api key>") as client:
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
logging.getLogger("makimoto.kawa.client").setLevel(
    logging.DEBUG
)  # this SDK's own events
logging.getLogger("httpx2").setLevel(logging.DEBUG)  # every request/response
```

See the [SDK API Reference](api-reference.md) for the full set of methods and models.
