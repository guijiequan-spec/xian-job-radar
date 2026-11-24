"""统一岗位数据模型。

字段设计原则：
- source: 数据来源平台，真实采集标注具体平台，推断数据标注 inferred
- verified: 是否为真实采集到的岗位（True=真实，False=推断/未验证）
- salary: 未登录时平台会打码（**-**元），如实记录，不杜撰
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional
import json
from datetime import datetime


@dataclass
class Job:
    title: str = ""
    company: str = ""
    city: str = ""
    district: str = ""
    salary: str = ""
    experience: str = ""
    education: str = ""
    tags: List[str] = field(default_factory=list)
    description: str = ""
    url: str = ""
    source: str = ""                 # zhilian / liepin / boss / linkedin / search
    source_name: str = ""            # 智联招聘 / 猎聘 / ...
    company_nature: str = "未识别"   # 外企 / 央国企 / 头部民企 / 其他 / 未识别
    match_score: float = 0.0
    match_reasons: List[str] = field(default_factory=list)
    verified: bool = True            # 真实采集=True；模型推断/搜索摘要可能不完整=False
    crawled_at: str = ""

    def __post_init__(self):
        if not self.crawled_at:
            self.crawled_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def key(self) -> str:
        # 用 公司+标题 做主键，URL 兜底
        base = f"{self.company}|{self.title}".strip()
        return base if base not in ("|", "") else self.url

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Job":
        return Job(**{k: v for k, v in d.items() if k in Job.__dataclass_fields__})


@dataclass
class SourceResult:
    """单个数据源的采集结果（含失败留痕）。"""
    source: str
    source_name: str
    status: str = "success"          # success / blocked / error / empty
    jobs: List[Job] = field(default_factory=list)
    error: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "source_name": self.source_name,
            "status": self.status,
            "count": len(self.jobs),
            "error": self.error,
            "note": self.note,
        }


def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=lambda o: o.to_dict() if hasattr(o, "to_dict") else str(o))


def dedup(jobs: List[Job]) -> List[Job]:
    seen = set()
    out = []
    for j in jobs:
        if j.key in seen:
            continue
        seen.add(j.key)
        out.append(j)
    return out
