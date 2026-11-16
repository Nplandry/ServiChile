from __future__ import annotations

from typing import Any

import httpx


def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 2.0,
) -> tuple[bool, Any, str | None]:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            r = client.get(url, params=params, headers=headers)
            r.raise_for_status()
            ctype = r.headers.get("content-type", "")
            if "json" in ctype:
                return True, r.json(), None
            return True, r.text, None
    except Exception as exc:  # noqa: BLE001
        return False, None, str(exc) or type(exc).__name__


def post_json(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 2.0,
) -> tuple[bool, Any, str | None]:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            return True, r.json(), None
    except Exception as exc:  # noqa: BLE001
        return False, None, str(exc) or type(exc).__name__
