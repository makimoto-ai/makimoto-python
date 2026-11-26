from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import Job


class KawaTimeoutError(TimeoutError):
    """Raised by ``transcribe()`` when the job isn't done within its time limit.

    The job is not cancelled: it carries on server-side, so pass ``job_id``
    to ``poll()`` or ``get_job()`` to pick it up again. A subclass of the
    built-in ``TimeoutError``, so ``except TimeoutError`` catches this too.

    Attributes:
        job_id (str): The job that was still running.
        last_job (Job): The job's state at the last check.
        waited (float): Seconds spent polling before giving up.
    """

    def __init__(self, job_id: str, last_job: Job, waited: float):
        """Initialise the error.

        Args:
            job_id (str): The job that was still running.
            last_job (Job): The job's state at the last check.
            waited (float): Seconds spent polling before giving up.
        """
        self.job_id = job_id
        self.last_job = last_job
        self.waited = waited
        super().__init__(
            f"Job {job_id} still {last_job.status} after {waited:.0f} s. It carries "
            "on server-side: pick it up with poll(job_id) or get_job(job_id)."
        )

    def __reduce__(self):
        # args holds only the message, so the default would call cls(message).
        return (type(self), (self.job_id, self.last_job, self.waited))


class KawaError(RuntimeError):
    """Raised when the API returns a non-2xx response.

    ``status_code``, ``body`` and ``headers`` are kept so callers can branch on,
    for example, a 401 (API key missing/invalid) versus a 404 (unknown job), and
    inspect response headers (such as ``Retry-After`` on a 429, or the ``Server``
    header that reveals whether a 413 came from the API or a proxy in front of it).

    Attributes:
        status_code (int): The response's HTTP status code.
        body (Any): The parsed response body (or ``{"raw": ...}`` if it
            wasn't valid JSON).
        url (str): The request URL that produced this response.
        headers (dict[str, str]): The response headers.
    """

    def __init__(
        self,
        status_code: int,
        body: Any,
        url: str,
        headers: dict[str, str] | None = None,
    ):
        """Initialise the error.

        Args:
            status_code (int): The response's HTTP status code.
            body (Any): The parsed response body.
            url (str): The request URL that produced this response.
            headers (dict[str, str] | None): The response headers, if any.
        """
        self.status_code = status_code
        self.body = body
        self.url = url
        self.headers = dict(headers or {})
        detail = ""
        if isinstance(body, dict):
            err = body.get("error")
            if isinstance(err, dict):
                detail = str(err.get("message") or err.get("code") or "")
            else:
                detail = str(body.get("message") or err or "")
        super().__init__(detail or f"HTTP {status_code}")


class KawaValidationError(KawaError):
    """Raised when a successful response doesn't match the expected shape.

    A subclass of ``KawaError``, so ``except KawaError`` catches
    this too.

    Attributes:
        validation_error (Exception): The underlying `pydantic.ValidationError`.
        status_code (int): The response's HTTP status code.
        body (Any): The parsed response body.
        url (str): The request URL that produced this response.
        headers (dict[str, str]): The response headers.
    """

    def __init__(
        self,
        status_code: int,
        body: Any,
        url: str,
        validation_error: Exception,
        headers: dict[str, str] | None = None,
    ):
        """Initialise the error.

        Args:
            status_code (int): The response's HTTP status code.
            body (Any): The parsed response body that failed validation.
            url (str): The request URL that produced this response.
            validation_error (Exception): The underlying
                `pydantic.ValidationError` this wraps.
            headers (dict[str, str] | None): The response headers, if any.
        """
        self.validation_error = validation_error
        self.status_code = status_code
        self.body = body
        self.url = url
        self.headers = dict(headers or {})
        RuntimeError.__init__(
            self,
            f"Response from {url} did not match the expected shape: {validation_error}",
        )
