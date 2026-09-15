# makimoto-kawa

<!-- Previous Version
[![CI](https://github.com/makimoto-ai/makimoto-python/actions/workflows/ci.yml/badge.svg)](https://github.com/makimoto-ai/makimoto-python/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/makimoto-kawa?cachebust=1)](https://pypi.org/project/makimoto-kawa/)
[![Python versions](https://img.shields.io/pypi/pyversions/makimoto-kawa?cachebust=1)](https://pypi.org/project/makimoto-kawa/)
[![License](https://img.shields.io/github/license/makimoto-ai/makimoto-python?cachebust=1)](https://github.com/makimoto-ai/makimoto-python/blob/main/LICENSE)
[![Discord Online](https://img.shields.io/discord/1352140878650540062?logo=discord&style=for-the-badge)]
-->

<p align="center">
    <a href="https://github.com/makimoto-ai/makimoto-python/actions/workflows/ci.yml"><img src="https://github.com/makimoto-ai/makimoto-python/actions/workflows/ci.yml/badge.svg" alt="GIT CI" /></a>
    <a href="https://pypi.org/project/makimoto-kawa/"><img src="https://img.shields.io/pypi/v/makimoto-kawa?cachebust=1" alt="PyPI Version"/></a>
    <a href="https://pypi.org/project/makimoto-kawa/"><img src="https://img.shields.io/pypi/pyversions/makimoto-kawa?cachebust=1" alt="Python Versions"/></a>
    <a href="https://www.makimoto.ai/"><img src="https://img.shields.io/badge/Website-Makimoto-blue?logo=googlechrome&logoColor=white" alt="Website" /></a>
    <a href="https://discord.gg/EwVQxPCb5"><img src="https://img.shields.io/discord/1352140878650540062?logo=discord&logoColor=white&label=Discord&color=5865F2" alt="Discord" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-red.svg" alt="MIT license" /></a>
</p>
    <!-- 
    Future Additions: 
    - # of Contributors
    - other repo reference websites
    GitHub APP
    <a href="https://github.com/apps/ecc-tools"><img src="https://img.shields.io/badge/GitHub%20App-ECC%20Tools-181717?logo=github&logoColor=white" alt="GitHub App" /></a> -->
    

Official Python SDK for [Kawa](https://github.com/makimoto-ai/kawa)'s transcription API. `makimoto` is the shared namespace this SDK lives under, `kawa` is the specific product it talks to, more Makimoto products may get their own subpackage here later.

This is the maintained, typed client, with `pydantic` response models, structured exceptions, and a tested, versioned release process, built on top of the same API as the reference client in the main `kawa` repo. For the interactive [playground](https://github.com/makimoto-ai/kawa/tree/main/demo), full [API docs](https://makimoto-ai.github.io/kawa/service/), and the [OpenAPI spec](https://github.com/makimoto-ai/kawa/blob/main/docs/openapi.json), see the main `kawa` repo. Prefer a zero-dependency, copy-paste client instead of a pip package? See [`kawa_client.py`](https://github.com/makimoto-ai/kawa/blob/main/demo/kawa_client.py) there.

## Install

Requires Python 3.10+.

```bash
pip install makimoto-kawa
```

## Authentication

Create an API key from the Makimoto dashboard: <https://www.makimoto.ai/login>. This is a static key, not the short-lived JWT your browser session uses, it doesn't expire on its own, and it's the only credential this SDK accepts, the transcription endpoints reject a dashboard login JWT outright.

```python
client = kawa.KawaClient(api_key="<your api key>")
```

or set it once as an environment variable and omit the argument entirely:

```bash
export MAKIMOTO_API_KEY="<your api key>"
```

An explicit `api_key` argument always wins over the environment variable if both are set.

## Usage

```python
from makimoto import kawa

client = kawa.KawaClient(api_key="<your api key>")  # or set MAKIMOTO_API_KEY instead

job = client.transcribe("call.mp3", language="en")

if job.status == "succeeded":
    print(job.result.full_text)
else:
    print(job.error)
```

See [`examples/quickstart.py`](https://github.com/makimoto-ai/makimoto-python/blob/main/examples/quickstart.py) for a complete, runnable script, it ships with a small sample audio file, so `python examples/quickstart.py` works out of the box once `MAKIMOTO_API_KEY` is set.

`transcribe()` submits the recording and polls until it's done in one call, raising `TimeoutError` if it never finishes. For manual control, e.g. streaming live status updates to a UI, the lower-level primitives are still there:

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
summary_job = client.create_summary(transcript_text="the customer called about a billing issue...")
```

Fetch or delete any job (transcription, summary, or tags) by its `job_id`:

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
for job in client.iter_jobs(status="succeeded"):
    print(job.job_id)
```

Release the client's connections when you're done with it, or use it as a context manager:

```python
with kawa.KawaClient(api_key="<your api key>") as client:
    ...
```

## Errors

Every call raises `kawa.KawaError` on an API-level failure (bad status code, or a response that doesn't match the expected shape), and `kawa.TimeoutError`-compatible `TimeoutError` from `transcribe()` if a job never finishes in time. A failed transcription job (`status == "failed"`) is not an exception, it's a normal result, check `.status`/`.error` as shown above.

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

## Development

See [`CONTRIBUTING.md`](https://github.com/makimoto-ai/makimoto-python/blob/main/CONTRIBUTING.md).

## Licence

[MIT](https://github.com/makimoto-ai/makimoto-python/blob/main/LICENSE)
