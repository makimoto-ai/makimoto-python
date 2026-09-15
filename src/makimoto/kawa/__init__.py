"""Client for the Makimoto Kawa transcription API.

Read this top to bottom to learn the HTTP contract: authenticate, list jobs,
submit a recording, poll until done, read the transcript.

    GET    /v1/transcriptions            -> list jobs
    POST   /v1/transcriptions            -> submit audio (multipart), returns job_id
    GET    /v1/transcriptions/{job_id}   -> job status + result when succeeded
    DELETE /v1/transcriptions/{job_id}   -> remove a job (where supported)
    POST   /v1/summarize                 -> summarise a succeeded transcription,
                                             returns job_id
    POST   /v1/tag                       -> tag a succeeded transcription,
                                             returns job_id

A summary or tags job is fetched/polled the same way as a transcription,
through its own ``job_id``.

Authenticate every request with an API key (create one from the dashboard):

    Authorization: Bearer <makimoto_api_key>

Example
-------
>>> from makimoto.kawa import KawaClient
>>> client = KawaClient(api_key="<your api key>")
>>> job = client.transcribe("call.mp3", language="en")
>>> if job.status == "succeeded":
...     print(job.result.full_text)
"""

from .client import DEFAULT_API_URL, KawaClient
from .exceptions import KawaError, KawaValidationError
from .models import (
    TERMINAL_STATUSES,
    Job,
    JobError,
    Segment,
    SummaryResult,
    TagsResult,
    TranscriptionPage,
    TranscriptResult,
)

__all__ = [
    "DEFAULT_API_URL",
    "TERMINAL_STATUSES",
    "Job",
    "JobError",
    "KawaClient",
    "KawaError",
    "KawaValidationError",
    "Segment",
    "SummaryResult",
    "TagsResult",
    "TranscriptResult",
    "TranscriptionPage",
]
