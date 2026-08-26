# Security policy

## Reporting a vulnerability

If you discover a security vulnerability in this SDK, please report it responsibly. **Do not file a public GitHub issue.**

Send your report to **contact@makimoto.ai** with the following information:

- A description of the vulnerability
- Steps to reproduce
- The potential impact
- Any suggested fix or mitigation, if you have one

You should receive an acknowledgement within two working days. We will work with you to validate the issue, develop a fix, and coordinate disclosure.

## Disclosure policy

We follow coordinated disclosure. We ask that you give us a reasonable time to investigate and address the vulnerability before any public disclosure. We will keep you informed of our progress throughout the process.

Once a fix is available, we will:

- Publish a security advisory on this repository
- Credit the reporter (if you wish to be credited)
- Release a patched version to PyPI

## Supported versions

Security updates apply to the latest published release on PyPI. As this SDK is pre-1.0, only the most recent `0.x` version is supported.

## Scope

This policy applies to the `makimoto-kawa` Python package and this repository's source code. For the Kawa API itself or the Makimoto website, see [kawa's security policy](https://github.com/makimoto-ai/kawa/blob/main/SECURITY.md) instead.

Out of scope: third-party dependencies (please report to the relevant upstream project, `httpx2` or `pydantic`) and infrastructure providers.
