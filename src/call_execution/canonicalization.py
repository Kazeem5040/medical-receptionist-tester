"""Canonical snapshots and stable hashes for call execution."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def to_canonical_data(value: Any, *, exclude_none: bool = True) -> Any:
    """Convert supported values into JSON-compatible canonical data."""

    if isinstance(value, BaseModel):
        return to_canonical_data(
            value.model_dump(mode="json", by_alias=True, exclude_none=exclude_none),
            exclude_none=exclude_none,
        )

    if isinstance(value, dict):
        return {
            str(key): to_canonical_data(item, exclude_none=exclude_none)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if not (exclude_none and item is None)
        }

    if isinstance(value, (list, tuple)):
        return [
            to_canonical_data(item, exclude_none=exclude_none)
            for item in value
            if not (exclude_none and item is None)
        ]

    return value


def canonical_json(value: Any, *, exclude_none: bool = True) -> str:
    """Serialize a value into stable, compact JSON."""

    return json.dumps(
        to_canonical_data(value, exclude_none=exclude_none),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def canonical_snapshot(value: Any, *, exclude_none: bool = True) -> dict[str, Any]:
    """Return a canonical JSON-compatible snapshot dictionary."""

    data = to_canonical_data(value, exclude_none=exclude_none)
    if not isinstance(data, dict):
        msg = "Canonical call execution snapshots must be dictionaries."
        raise TypeError(msg)
    return data


def stable_fingerprint(
    value: Any,
    *,
    prefix: str = "sha256",
    exclude_none: bool = True,
) -> str:
    """Create a stable SHA-256 fingerprint for reproducibility."""

    digest = hashlib.sha256(
        canonical_json(value, exclude_none=exclude_none).encode("utf-8"),
    ).hexdigest()
    return f"{prefix}:{digest}"
