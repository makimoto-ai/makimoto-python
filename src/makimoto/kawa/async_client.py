from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import httpx2

from ._base import DEFAULT_API_URL, _BaseKawaClient
from .exceptions import KawaError
from .models import Job, TranscriptionPage

# See client.py's own logger comment: same rationale, own logger (own
# NullHandler) since this is a sibling module, not a parent/child of
# "makimoto.kawa.client", so its NullHandler wouldn't be found via
# propagation.
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class AsyncKawaClient(_BaseKawaClient):
    """Async counterpart of `KawaClient`, same API, `httpx2.AsyncClient` transport.

    Every endpoint method here is `async def` and awaits its request; use
    this instead of `KawaClient` inside an existing event loop (an async
    web app, an async worker) rather than blocking it with sync I/O.

    Credentials: pass ``api_key`` explicitly, or omit it and set the
    ``MAKIMOTO_API_KEY`` environment variable instead, the explicit
    argument always wins if both are present. Neither being set doesn't
    raise here, only lazily, the first time a method actually sends a
    request. This is a static API key (create one from the dashboard),
    not the short-lived dashboard login JWT, the transcription endpoints
    this client calls no longer accept that.

    Transport: uses ``httpx2.AsyncClient`` internally, one instance per
    ``AsyncKawaClient``, reused across calls, with ``follow_redirects=True``
    set explicitly (not the library default, kept to match `KawaClient`'s
    behaviour).

    Attributes:
        api_key (str): API key, stripped of surrounding whitespace.
        api_url (str): Base URL for the API, trailing slash removed.
        timeout (float): Default per-request timeout, in seconds.
        last_status (int | None): HTTP status code of the most recent
            response, or ``None`` before any request has been made.
        last_headers (dict[str, str]): Headers of the most recent response.
        last_url (str | None): URL of the most recent response, or ``None``
            before any request has been made.

    Examples:
        >>> async with AsyncKawaClient(api_key="<your api key>") as client:
        ...     job = await client.transcribe("call.mp3", language="en")
        ...     print(job.result.full_text)
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str = DEFAULT_API_URL,
        *,
        timeout: float = 30.0,
        session: httpx2.AsyncClient | None = None,
    ):
        """Initialise the client.

        Args:
            api_key (str | None): API key. If omitted, falls back to
                the environment variable.
            api_url (str): Base URL for the API.
            timeout (float): Default per-request timeout, in seconds.
            session (httpx2.AsyncClient | None): Existing HTTP client to
                reuse. If omitted, a new one is created with
                ``follow_redirects=True``.
        """
        if api_key is None:
            api_key = os.environ.get("MAKIMOTO_API_KEY", "")
            logger.debug(
                "no api_key argument given, using MAKIMOTO_API_KEY (%s)",
                "found" if api_key else "not set",
            )
        super().__init__(api_key, api_url, timeout)
        self._session = session or httpx2.AsyncClient(follow_redirects=True)

    async def aclose(self) -> None:
        """Close the underlying HTTP session, releasing pooled connections.

        `AsyncKawaClient` holds one persistent `httpx2.AsyncClient` for its
        whole lifetime. Closing it doesn't matter for a short script, the
        process exit cleans it up either way, but does matter for a
        long-running app that keeps a client around, a server, a worker,
        and so on.
        """
        await self._session.aclose()

    async def __aenter__(self) -> AsyncKawaClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    # -- internals ---------------------------------------------------------- #

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """The one place every HTTP call goes through.

        Records `last_status`/`last_headers` for debugging, parses the JSON
        body (falls back to `{"raw": response.text}` if it isn't valid
        JSON), and raises `KawaError` on any status >= 400.

        Args:
            method (str): HTTP method, e.g. ``"GET"`` or ``"POST"``.
            path (str): Request path, appended to ``api_url``.
            **kwargs (Any): Forwarded to ``httpx2.AsyncClient.request``; a
                ``timeout`` key overrides ``self.timeout`` for this call.

        Returns:
            Any: The parsed JSON response body.

        Raises:
            KawaError: If the response status is 400 or above.
        """
        # Upload streams the file, so allow a longer timeout for POST.
        timeout = kwargs.pop("timeout", self.timeout)
        response = await self._session.request(
            method, self._url(path), headers=self._headers(), timeout=timeout, **kwargs
        )
        self.last_status = response.status_code
        self.last_headers = dict(response.headers)
        self.last_url = str(response.url)
        try:
            body = response.json() if response.content else {}
        except ValueError:
            body = {"raw": response.text}
        if response.status_code >= 400:
            raise KawaError(
                response.status_code,
                body,
                self.last_url,
                headers=dict(response.headers),
            )
        return body

    # -- endpoints ---------------------------------------------------------- #

    async def list_jobs(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        status: str | None = None,
        job_type: str | None = None,
        language: str | None = None,
        created_after: str | None = None,
        job_id: str | None = None,
    ) -> TranscriptionPage:
        """GET /v1/transcriptions - one page of jobs for the authenticated account.

        Keyset-paginated: ``limit`` defaults to 10 server-side and is capped
        at 100; pass ``cursor=page.next_cursor`` to fetch the next page,
        ``next_cursor`` is ``None`` once there's nothing left. ``status``,
        ``job_type`` (``"transcription"``, ``"summary"``, or ``"tags"``),
        ``language``, ``created_after`` (an ISO 8601 timestamp), and
        ``job_id`` (a UUID) are optional filters, composed with AND where
        more than one is given. With no ``job_type``, every job type is
        returned, the API applies no implicit filter of its own.

        Every argument is passed straight through as a query parameter (
        ``job_type`` as ``type``), an invalid value (e.g. an unrecognised
        ``status``) raises `KawaError` from the backend rather than being
        validated here, that keeps this client from carrying its own copy
        of rules the API already owns.
        """
        params = {
            "limit": limit,
            "cursor": cursor,
            "status": status,
            "type": job_type,
            "language": language,
            "created_after": created_after,
            "job_id": job_id,
        }
        query = {k: v for k, v in params.items() if v is not None}
        body = await self._request("GET", "/v1/transcriptions", params=query)
        return self._parse(TranscriptionPage, body)

    async def iter_jobs(
        self,
        *,
        page_size: int | None = None,
        status: str | None = None,
        job_type: str | None = None,
        language: str | None = None,
        created_after: str | None = None,
        job_id: str | None = None,
    ) -> AsyncIterator[Job]:
        """Yield every matching job, fetching further pages automatically.

        A thin wrapper around `list_jobs()` for the common case of wanting
        all matching jobs rather than one page at a time. `page_size`
        controls the underlying per-request `limit` (server default 10, capped
        at 100), not how many jobs this yields overall, use `list_jobs`
        directly if you need explicit control over paging instead.
        """
        cursor: str | None = None
        while True:
            page = await self.list_jobs(
                limit=page_size,
                cursor=cursor,
                status=status,
                job_type=job_type,
                language=language,
                created_after=created_after,
                job_id=job_id,
            )
            for job in page.transcriptions:
                yield job
            if page.next_cursor is None:
                return
            cursor = page.next_cursor

    async def create_transcription(
        self,
        file_path: str | Path,
        *,
        language: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Job:
        """POST /v1/transcriptions - submit a recording as multipart form-data.

        Reads `file_path` with a plain, blocking `open()`, there's no async
        file I/O here, so a large file on a slow disk will still occupy the
        event loop for that read. Fine for the typical case (an audio file
        read from local/network storage); if that's a problem for your
        workload, read the file yourself off-thread and adapt this method.

        Args:
            file_path (str | Path): Path to the audio/video file to upload.
            language (str | None): Optional language hint for transcription.
            metadata (dict[str, Any] | None): Optional metadata to attach to
                the job, sent as a JSON string.

        Returns:
            Job: The newly created job (typically ``queued`` or ``processing``).

        Raises:
            KawaError: If the API returns a non-2xx response.
            KawaValidationError: If the response doesn't match `Job`'s shape.
        """
        path = Path(file_path)
        data: dict[str, str] = {}
        if language:
            data["language"] = language.strip()
        if metadata:
            data["metadata"] = json.dumps(metadata, separators=(",", ":"))
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        with path.open("rb") as handle:
            body = await self._request(
                "POST",
                "/v1/transcriptions",
                files={"file": (path.name, handle, mime)},
                data=data,
                timeout=120.0,
            )
        return self._parse(Job, body)

    async def get_job(self, job_id: str) -> Job:
        """GET /v1/transcriptions/{job_id} - status, and result once done.

        Args:
            job_id (str): The job's identifier.

        Returns:
            Job: The job's current state.

        Raises:
            KawaError: If the API returns a non-2xx response.
            KawaValidationError: If the response doesn't match `Job`'s shape.
        """
        body = await self._request("GET", f"/v1/transcriptions/{job_id}")
        return self._parse(Job, body)

    async def delete_job(self, job_id: str) -> dict[str, Any]:
        """DELETE /v1/transcriptions/{job_id} - remove a job, where supported.

        Works for any job type (transcription, summary, or tags).

        Deleting a transcription does not delete summaries or tags derived from it;
        delete those separately by their own ``job_id``.

        Args:
            job_id (str): The job's identifier.

        Returns:
            dict[str, Any]: The API's response body.

        Raises:
            KawaError: If the API returns a non-2xx response.
        """
        # _request() is genuinely Any (a response body could be any JSON
        # shape); DELETE's contract is known to be a dict, so cast rather
        # than widen this method's own, more useful, return type.
        body = await self._request("DELETE", f"/v1/transcriptions/{job_id}")
        return cast(dict[str, Any], body)

    async def create_summary(
        self,
        transcription_job_id: str | None = None,
        *,
        transcript_text: str | None = None,
    ) -> Job:
        """POST /v1/summarize - create a summary job from a transcript.

        Exactly one of ``transcription_job_id`` or ``transcript_text`` must
        be given, the API rejects zero or both with a 400.

        Args:
            transcription_job_id (str | None): One of the caller's own
                transcription jobs, in status ``succeeded``. Mutually
                exclusive with ``transcript_text``.
            transcript_text (str | None): A transcript supplied directly,
                with no transcription job behind it. Mutually exclusive
                with ``transcription_job_id``.

        Returns:
            Job: The newly created job (``type="summary"``, typically
                ``processing``).

        Raises:
            KawaError: If the API returns a non-2xx response, including a
                400 when neither or both of the two arguments are given.
            KawaValidationError: If the response doesn't match `Job`'s shape.
        """
        body: dict[str, str] = {}
        if transcription_job_id is not None:
            body["transcription_job_id"] = transcription_job_id
        if transcript_text is not None:
            body["transcript_text"] = transcript_text
        return self._parse(Job, await self._request("POST", "/v1/summarize", json=body))

    async def create_tags(
        self,
        transcription_job_id: str | None = None,
        *,
        transcript_text: str | None = None,
    ) -> Job:
        """POST /v1/tag - create a tags job from a transcript.

        Exactly one of ``transcription_job_id`` or ``transcript_text`` must be given,
        the API rejects zero or both with a 400.

        Note that the tag taxonomy is fixed by the service and isn't configurable
        per account.

        Args:
            transcription_job_id (str | None): One of the caller's own
                transcription jobs, in status ``succeeded``. Mutually
                exclusive with ``transcript_text``.
            transcript_text (str | None): A transcript supplied directly,
                with no transcription job behind it. Mutually exclusive
                with ``transcription_job_id``.

        Returns:
            Job: The newly created job (``type="tags"``, typically
                ``processing``).

        Raises:
            KawaError: If the API returns a non-2xx response, including a
                400 when neither or both of the two arguments are given.
            KawaValidationError: If the response doesn't match `Job`'s shape.
        """
        body: dict[str, str] = {}
        if transcription_job_id is not None:
            body["transcription_job_id"] = transcription_job_id
        if transcript_text is not None:
            body["transcript_text"] = transcript_text
        return self._parse(Job, await self._request("POST", "/v1/tag", json=body))

    async def poll(
        self,
        job_id: str,
        *,
        interval: float = 2.0,
        max_attempts: int = 60,
    ) -> AsyncIterator[Job]:
        """Yield the job on each poll until it reaches a terminal status.

        Poll ``GET /v1/transcriptions/{job_id}`` every ``interval`` seconds while
        the status is ``queued`` or ``processing``; stop on ``succeeded`` or
        ``failed``. Yielding (rather than blocking) lets a UI show live updates.
        Gives up silently after ``max_attempts``, use ``transcribe()`` instead if
        you want a clear exception on timeout.

        Args:
            job_id (str): The job's identifier.
            interval (float): Seconds to sleep between polls.
            max_attempts (int): Maximum number of polls before giving up.

        Yields:
            Job: The job's state on each poll.

        Raises:
            KawaError: If the API returns a non-2xx response.
            KawaValidationError: If a response doesn't match `Job`'s shape.
        """
        last_status = None
        for attempt in range(max_attempts):
            job = await self.get_job(job_id)
            last_status = job.status
            yield job
            if job.is_terminal:
                return
            if attempt < max_attempts - 1:
                await asyncio.sleep(interval)
        if max_attempts > 0:
            logger.warning(
                "poll() gave up on job %s after %d attempts, still %s, "
                "no exception was raised, check the last yielded Job's "
                ".is_terminal yourself (or use transcribe() instead, which "
                "raises TimeoutError for this case)",
                job_id,
                max_attempts,
                last_status,
            )

    async def transcribe(
        self,
        file_path: str | Path,
        *,
        language: str | None = None,
        metadata: dict[str, Any] | None = None,
        interval: float = 2.0,
        max_attempts: int = 60,
    ) -> Job:
        """Submit and poll in one call. Raises on timeout, not on a failed job.

        A ``failed`` job is a normal outcome (bad audio, unsupported language),
        not a malfunction, returned like ``get_job()`` would, check
        ``.status``/``.error``. Only exhausting ``max_attempts`` without reaching
        a terminal status raises, since that's genuinely exceptional.

        Args:
            file_path (str | Path): Path to the audio/video file to upload.
            language (str | None): Optional language hint for transcription.
            metadata (dict[str, Any] | None): Optional metadata to attach to
                the job.
            interval (float): Seconds to sleep between polls.
            max_attempts (int): Maximum number of polls before giving up.

        Returns:
            Job: The job in its terminal state (``succeeded`` or ``failed``).

        Raises:
            TimeoutError: If ``max_attempts`` is exhausted before the job
                reaches a terminal status.
            KawaError: If the API returns a non-2xx response.
            KawaValidationError: If a response doesn't match `Job`'s shape.
        """
        job = await self.create_transcription(
            file_path, language=language, metadata=metadata
        )
        final = job
        async for update in self.poll(
            job.job_id, interval=interval, max_attempts=max_attempts
        ):
            final = update
        if not final.is_terminal:
            raise TimeoutError(
                f"Job {job.job_id} still processing after {max_attempts} checks"
            )
        return final
