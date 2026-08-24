"""Client for the Makimoto Kawa transcription API.

Read this top to bottom to learn the HTTP contract: authenticate, list jobs,
submit a recording, poll until done, read the transcript.

    GET    /v1/transcriptions            -> list jobs
    POST   /v1/transcriptions            -> submit audio (multipart), returns job_id
    GET    /v1/transcriptions/{job_id}   -> job status + transcript when succeeded
    DELETE /v1/transcriptions/{job_id}   -> remove a job (where supported)

Authenticate every request with a dashboard token:

    Authorization: Bearer <makimoto_api_token>

Example
-------
>>> from makimoto.kawa import KawaClient
>>> client = KawaClient(token="<dashboard-token>")
>>> job = client.transcribe("call.mp3", language="en")
>>> if job.status == "succeeded":
...     print(job.result.full_text)
"""

from .client import DEFAULT_API_URL, KawaClient
from .exceptions import KawaError, KawaValidationError
from .models import Job, JobError, Segment, TERMINAL_STATUSES, TranscriptResult, Usage

__all__ = [
    "KawaClient",
    "KawaError",
    "KawaValidationError",
    "Job",
    "JobError",
    "Segment",
    "TranscriptResult",
    "Usage",
    "DEFAULT_API_URL",
    "TERMINAL_STATUSES",
]
