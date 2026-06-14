import re

from zyfangji_retrieval.domain.models import FormulaMappingStatus, FormulaMention


AMBIGUITY_PATTERN = re.compile(r"[；;]|(?:^|\s)[一二三四五六七八九十0-9]+[.、]|/|或|偏寒|偏热")
FORMULA_NAME_PATTERN = re.compile(r"[\u4e00-\u9fffA-Za-z0-9（）()·]+?[汤丸散饮方剂]")
LEADING_CONNECTORS = "或及和、，,；;/：:"


def parse_formula_mentions(formula_raw: str) -> list[FormulaMention]:
    text = formula_raw.strip()
    if not text:
        return []

    needs_review = AMBIGUITY_PATTERN.search(text) is not None
    mentions: list[FormulaMention] = []
    seen: set[str] = set()
    for match in FORMULA_NAME_PATTERN.finditer(text):
        name = match.group(0).strip(LEADING_CONNECTORS)
        if not name or name in seen:
            continue
        seen.add(name)
        mentions.append(
            FormulaMention(
                name=name,
                needs_review=needs_review,
                raw_text=text if needs_review else None,
            )
        )
    return mentions


def formula_mapping_status(
    formula_raw: str, mentions: list[FormulaMention]
) -> FormulaMappingStatus:
    if not formula_raw.strip():
        return "missing"
    if AMBIGUITY_PATTERN.search(formula_raw):
        return "needs_review"
    if mentions:
        return "parsed"
    return "unmapped"
