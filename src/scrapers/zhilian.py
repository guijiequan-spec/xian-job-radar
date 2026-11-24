"""智联招聘公开搜索页采集。

已验证：https://www.zhaopin.com/jobs/?jl=854&kw=关键词
公开页服务端直出 job-card，含职位/公司/地点/JD摘要/经验学历/链接。
未登录时薪资字段为 **-**元（打码），如实记录，不杜撰。
"""

import re
import html as htmlmod
from urllib.parse import quote

from ..models import Job, SourceResult
from ..config import ZHILIAN_CITY_CODE, BLOCK_WORDS
from .http import get, robots_allowed

BASE = "https://www.zhaopin.com"


def _clean(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmlmod.unescape(s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def parse_list(html: str, keyword: str) -> list:
    """从列表页 HTML 解析岗位。按 job-card 块切分。"""
    jobs = []
    # 每个岗位以 <div class="job-card ..."> 开始
    blocks = re.split(r'<div class="job-card(?:\s|")', html)
    for blk in blocks[1:]:
        # 标题 + 链接
        m = re.search(r'class="[^"]*job-card__name[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', blk, re.S)
        if not m:
            m = re.search(r'<a[^>]*href="([^"]+)"[^>]*class="[^"]*job-card__name[^"]*"[^>]*>(.*?)</a>', blk, re.S)
        if not m:
            continue
        url = htmlmod.unescape(m.group(1))
        title = _clean(m.group(2))
        # 公司
        cm = re.search(r'class="[^"]*job-card__company-name[^"]*"[^>]*>(.*?)</a>', blk, re.S)
        company = _clean(cm.group(1)) if cm else ""
        # 薪资
        sm = re.search(r'class="job-card__salary"[^>]*>(.*?)</span>', blk, re.S)
        salary = _clean(sm.group(1)) if sm else ""
        # 地点
        lm = re.search(r'class="job-card__location"[^>]*>.*?<span[^>]*>(.*?)</span>', blk, re.S)
        location = _clean(lm.group(1)) if lm else ""
        city = location.split()[0] if location else "西安"
        district = " ".join(location.split()[1:]) if len(location.split()) > 1 else ""
        # 标签
        tags = [_clean(x) for x in re.findall(r'class="job-card__skill-tag"[^>]*>(.*?)</span>', blk, re.S)]
        tags = [t for t in tags if t]
        # JD 摘要
        dm = re.search(r'class="job-card__seo-description"[^>]*>(.*?)</p>', blk, re.S)
        desc = _clean(dm.group(1)) if dm else ""
        # 反垃圾过滤
        blob = title + company + desc
        if any(w in blob for w in BLOCK_WORDS):
            continue
        jobs.append(Job(
            title=title, company=company, city=city, district=district,
            salary=salary, experience=next((t for t in tags if "年" in t), ""),
            education=next((t for t in tags if t in ("大专", "本科", "硕士", "博士")), ""),
            tags=tags, description=desc, url=url,
            source="zhilian", source_name="智联招聘", verified=True,
        ))
    return jobs


def collect(keywords: list, max_per_keyword: int = 20) -> SourceResult:
    result = SourceResult(source="zhilian", source_name="智联招聘")
    if not robots_allowed(BASE, "/jobs/"):
        result.status = "blocked"
        result.note = "robots.txt 未明确允许 /jobs/ 路径，按保守原则跳过（可在配置中开启强制模式）"
        return result

    seen = set()
    for kw in keywords:
        url = f"{BASE}/jobs/?jl={ZHILIAN_CITY_CODE}&kw={quote(kw)}"
        html = get(url, referer=BASE + "/", delay=1.2)
        if not html:
            result.error = f"关键词「{kw}」请求失败"
            continue
        if "访问过于频繁" in html or "验证码" in html or "安全验证" in html[:3000]:
            result.status = "blocked"
            result.error = f"关键词「{kw}」触发反爬验证"
            break
        page_jobs = parse_list(html, kw)
        added = 0
        for j in page_jobs:
            if j.key in seen:
                continue
            seen.add(j.key)
            result.jobs.append(j)
            added += 1
            if added >= max_per_keyword:
                break
        print(f"  [智联] 关键词「{kw}」解析 {len(page_jobs)} 条，入库 {added} 条")
        if not page_jobs:
            result.note = (result.note + "；" if result.note else "") + f"「{kw}」解析0条（可能页面结构变化或需登录）"

    if not result.jobs and result.status == "success":
        result.status = "empty"
    return result
