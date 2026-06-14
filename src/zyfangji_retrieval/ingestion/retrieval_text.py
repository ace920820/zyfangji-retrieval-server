from collections.abc import Mapping


SOURCE_HEADERS = [
    "编码",
    "人模分类",
    "主干部位",
    "分支部位",
    "主病主症",
    "复合症(适应证)",
    "细分主症",
    "同症异名(方言别名）",
    "人模图示(症状在人体模型上定位显示）",
    "舌诊",
    "脉象",
    "伤寒论原文条文号",
    "中医证型",
    "中医病名",
    "病因（含得病时间 外感 内伤 误治 复发等）",
    "病理",
    "汇通西医病名",
    "中西先后（先看中医？先看西医？）",
    "治法",
    "推荐方剂",
    "推荐方剂配伍中药与西医检查化验指标禁忌",
    "疗效评定",
]

RETRIEVAL_FIELDS = [
    ("部位", ["主干部位", "分支部位"]),
    ("主症", ["主病主症"]),
    ("复合症", ["复合症(适应证)"]),
    ("细分主症", ["细分主症"]),
    ("同症异名", ["同症异名(方言别名）"]),
    ("舌诊", ["舌诊"]),
    ("脉象", ["脉象"]),
    ("证型", ["中医证型"]),
]


def build_retrieval_text(row: Mapping[str, str]) -> str:
    sections: list[str] = []
    for label, fields in RETRIEVAL_FIELDS:
        values = [str(row.get(field, "")).strip() for field in fields]
        values = [value for value in values if value]
        if values:
            sections.append(f"{label}:\n" + "\n".join(values))
    return "\n\n".join(sections)
