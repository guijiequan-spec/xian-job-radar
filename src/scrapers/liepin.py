"""猎聘公开搜索页采集适配器。

猎聘公开列表页多为服务端渲染 + JSON 内嵌，结构随版本变化较快。
本适配器尽力解析；若结构变化或需登录，返回 blocked/empty 并留痕，不虚构岗位。
"""

import re
import json
import html as htmlmod
from urllib.parse import quote

from ..models import Job, SourceResult
from ..config import LIEPIN_CITY_CODE, BLOCK_WORDS
from .http import get, robots_allowed

BASE = "https://www.liepin.com"


def _clean(s):
    return re.sub(r"\s+", " ", htmlmod.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def parse_list(html_text: str) -> list:
    jobs = []
    # 尝试 1: 内嵌 JSON (window.__NUXT__ / __INITIAL_STATE__ 中的 job 数组)
    json_jobs = []
    for m in re.finditer(r'"(jobTitle|jobName|title)"\s*:\s*"([^"]{2,60})"', html_text):
        json_jobs.append(m.group(2))
    # 尝试 2: DOM job-card / job-detail-box
    blocks = re.split(r'class="[^"]*(?:job-card|job-detail-box|job-item)[^"]*"', html_text)
    for blk in blocks[1:]:
        tm = re.search(r'class="[^"]*(?:job-title|job-name)[^"]*"[^>]*>(?:<[^>]+>)*\s*([^<]{2,60})', blk, re.S)
        title = _clean(tm.group(1)) if tm else ""
        if not title:
            continue
        cm = re.search(r'class="[^"]*(?:company-name|company__name)[^"]*"[^>]*>(?:<[^>]+>)*\s*([^<]{2,60})', blk, re.S)
        company = _clean(cm.group(1)) if cm else ""
        um = re.search(r'href="(https?://[^"]*job[^"]*)"', blk)
        url = htmlmod.unescape(um.group(1)) if um else ""
        sm = re.search(r'class="[^"]*(?:salary|job-salary)[^"]*"[^>]*>\s*([^<]{1,30})', blk, re.S)
        salary = _clean(sm.group(1)) if sm else ""
        jobs.append(Job(title=title, company=company, salary=salary, url=url,
                        source="liepin", source_name="猎聘", verified=True))
    return jobs


def collect(keywords: list, max_per_keyword: int = 15) -> SourceResult:
    result = SourceResult(source="liepin", source_name="猎聘")
    allowed = robots_allowed(BASE, "/zhaopin/")
    if not allowed:
        result.status = "blocked"
        result.note = "robots.txt 未明确允许 /zhaopin/，保守跳过"
        return result

    seen = set()
    for kw in keywords[:8]:  # 控制请求量
        url = f"{BASE}/zhaopin/?city={LIEPIN_CITY_CODE}&key={quote(kw)}"
        html = get(url, referer=BASE + "/", delay=1.5)
        if not html:
            result.error = f"关键词「{kw}」请求失败"
            continue
        if any(x in html[:3000] for x in ("验证码", "安全验证", "访问频繁", "滑块")):
            result.status = "blocked"
            result.error = f"关键词「{kw}」触发反爬验证"
            break
        page_jobs = parse_list(html)
        added = 0
        for j in page_jobs:
            if j.key in seen:
                continue
            seen.add(j.key)
            result.jobs.append(j)
            added += 1
            if added >= max_per_keyword:
                break
        print(f"  [猎聘] 关键词「{kw}」解析 {len(page_jobs)} 条，入库 {added} 条")
    if not result.jobs and result.status == "success":
        result.status = "empty"
        result.note = result.note or "公开页结构可能已变化或需登录，未解析到岗位"
    return result
