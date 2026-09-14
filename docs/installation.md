# Installation

*Last updated: 2026-08-26*

Requires Python 3.10+.

```bash
pip install makimoto-kawa
```

## Authentication

Create an API key from the Makimoto dashboard: <https://www.makimoto.ai/login>. This is a static key, not the short-lived JWT your browser session uses, it doesn't expire on its own, and it's the only credential this SDK accepts.

For more information, see the [Authentication](https://makimoto-ai.github.io/kawa/service/authentication/) page in the main documentation.

Pass the API key directly:

```python
client = kawa.KawaClient(api_key="<your api key>")
```

or set it once as an environment variable and omit the argument entirely:

```bash
export MAKIMOTO_API_KEY="<your api key>"
```

An explicit `api_key` argument always wins over the environment variable if both are set.
