# Installation

*Last updated: 2026-08-26*

Requires Python 3.10+.

```bash
pip install makimoto-kawa
```

## Authentication

Get a token from the Makimoto dashboard: <https://www.makimoto.ai/login>.

For now, this is a short-lived JWT, not a persistent API key: it expires, so copy a fresh one from the dashboard if requests start failing with `401`. This will change to a static API key in the near future; when it does, the same `token`/`MAKIMOTO_API_TOKEN` mechanism below will keep working, only what you paste in changes.

For more information, see the [Authentication](https://makimoto-ai.github.io/kawa/service/authentication/) page in the main documentation.

Pass the token directly:

```python
client = kawa.KawaClient(token="<dashboard-token>")
```

or set it once as an environment variable and omit the argument entirely:

```bash
export MAKIMOTO_API_TOKEN="<dashboard-token>"
```

An explicit `token` argument always wins over the environment variable if both are set.
