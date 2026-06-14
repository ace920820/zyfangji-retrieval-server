from pathlib import Path
from typing import Sequence

from zyfangji_retrieval.domain.models import KnowledgeEntry


def export_entries_jsonl(entries: Sequence[KnowledgeEntry], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(entry.model_dump_json() + "\n")


def load_entries_jsonl(path: Path) -> list[KnowledgeEntry]:
    entries: list[KnowledgeEntry] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                entries.append(KnowledgeEntry.model_validate_json(line))
    return entries
