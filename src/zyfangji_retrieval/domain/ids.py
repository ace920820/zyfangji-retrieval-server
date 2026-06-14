import hashlib
from collections.abc import Sequence


def content_fingerprint(parts: Sequence[str]) -> str:
    normalized = "\n".join(str(part).strip() for part in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def make_entry_id(parts: Sequence[str]) -> str:
    return f"shl_{content_fingerprint(parts)[:16]}"
