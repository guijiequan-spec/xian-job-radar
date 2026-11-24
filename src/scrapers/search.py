"""搜索引擎聚合（兜底源）。

通过 360 搜索 / 搜狗 搜素公开 indexed 的招聘页标题，
提取「岗位 + 公司」线索。这类结果来自公开搜索索引，标注 verified=False，
与平台直采严格区分，不杜撰薪资/链接以外的字段。
"""

import re
import html as htmlmod
from urllib.parse import quote, urlparse, parse_qs, unquote

from ..models import Job, SourceResult
from ..config import BLOCK_WORDS
from .http import get

SOURCES = [
    ("so360", "360搜索", "https://www.so.com/s?q="),
    ("sogou", "搜狗搜索", "https://www.sogou.com/web?query="),
]


def _clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", htmlmod.unescape(s)).strip()


def parse_360(html_text: str) -> list:
    jobs = []
    for m in re.finditer(r'<h3[^>]*>(.*?)</h3>', html_text, re.S):
        title = _clean(m.group(1))
        if not title or any(w in title for w in BLOCK_WORDS):
            continue
        jobs.append(title)
    return jobs


def parse_sogou(html_text: str) -> list:
    jobs = []
    for m in re.finditer(r'<h3[^>]*>(.*?)</h3>', html_text, re.S):
        title = _clean(m.group(1))
        if title:
            jobs.append(title)
    return jobs


def collect(keywords: list, max_total: int = 25) -> SourceResult:
    result = SourceResult(source="search", source_name="搜索引擎聚合")
    seen = set()
    queries = [f"西安 {kw} 招聘 2026" for kw in keywords[:6]]
    for skey, sname, base in SOURCES:
        for q in queries:
            if len(result.jobs) >= max_total:
                break
            url = base + quote(q)
            html = get(url, referer="https://www.so.com/" if "so" in skey else "https://www.sogou.com/", delay=2.0, retries=1)
            if not html:
                continue
            titles = parse_360(html) if skey == "so360" else parse_sogou(html)
            for t in titles:
                # 只保留看起来像招聘标题的（含岗位词或"招聘"）
                if len(result.jobs) >= max_total:
                    break
                if not any(k in t for k in ("招聘", "总监", "经理", "研究", "合作", "事务", "HR", "人力", "主管", "负责人")):
                    continue
                if t in seen:
                    continue
                seen.add(t)
                # 从标题粗拆公司与岗位：以" - "或"-"分隔
                parts = re.split(r"\s*[-|—_]\s*", t)
                title = parts[0][:40] if parts else t[:40]
                company = parts[1][:30] if len(parts) > 1 else ""
                j = Job(
                    title=title, company=company, city="西安",
                    url=url, source="search", source_name=sname,
                    verified=False,  # 搜索摘要，标注未验证
                    description="来源：公开搜索索引摘要，薪资与详情请以原页面为准",
                )
                result.jobs.append(j)
        if len(result.jobs) >= max_total:
            break
    if not result.jobs:
        result.status = "empty"
        result.note = "搜索引擎未返回可用岗位线索"
    else:
        result.note = "来自公开搜索索引摘要，字段可能不完整（薪资/详情以原页面为准），已标注 verified=False"
    return result
