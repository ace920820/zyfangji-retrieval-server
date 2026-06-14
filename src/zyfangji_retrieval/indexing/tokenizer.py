from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import jieba


@lru_cache(maxsize=1)
def _dictionary_terms(dictionary_path: str | None = None) -> tuple[str, ...]:
    path = Path(dictionary_path) if dictionary_path is not None else Path(__file__).with_name(
        "tcm_terms.txt"
    )
    if not path.exists():
        return ()
    terms = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        term = raw_line.strip()
        if term:
            terms.append(term)
    return tuple(terms)


@lru_cache(maxsize=1)
def load_tcm_dictionary(dictionary_path: Path | None = None) -> None:
    for term in _dictionary_terms(str(dictionary_path) if dictionary_path is not None else None):
        jieba.add_word(term)


def tokenize_chinese_text(text: str) -> list[str]:
    load_tcm_dictionary()
    tokens = jieba.lcut(text or "", cut_all=False)
    return [token.strip() for token in tokens if token and token.strip()]
