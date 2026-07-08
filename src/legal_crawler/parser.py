"""Synchronous text-parsing helpers.

Pure functions with no IO.  Endpoint-specific JSON → Pydantic parsing
now lives in the ``api/`` modules (``api/search.py``, ``api/detail.py``,
etc.) so each business domain owns its own response handling.
"""

import re

# Regex to strip ``<em class='highlight'>…</em>`` wrappers from titles.
_HIGHLIGHT_RE = re.compile(r"<em[^>]*>(.*?)</em>", re.DOTALL)


def strip_highlight_tags(text: str) -> str:
    """Remove ``<em class='highlight'>`` wrappers from *text*."""
    return _HIGHLIGHT_RE.sub(r"\1", text)
