"""简历匹配评分器。

画像来源：权贵杰《通用版简历2026》——
- 15年HR + 猎聘大数据研究院副院长 + 人大HR博士 + 高级经济师 + 中共党员 + 西安
- 选定方向：政企合作/公共事务、HRD、行业研究/战略
评分透明可解释：每条岗位给出 score 与命中的 reasons。
"""

from .models import Job
from .config import (
    DIRECTIONS, SENIORITY_KEYWORDS, SCORE_WEIGHTS, detect_company_nature,
)


def score_job(job: Job) -> Job:
    reasons = []
    score = 0.0
    title = job.title or ""
    company = job.company or ""
    desc = job.description or ""
    tags = " ".join(job.tags or [])
    blob = f"{title} {desc} {tags}"

    # 1) 标题命中目标岗位关键词（核心）
    hit_kws = [kw for kw in _all_title_kws() if kw.lower() in title.lower()]
    if hit_kws:
        score += SCORE_WEIGHTS["title_exact"]
        reasons.append(f"岗位标题命中：{'、'.join(hit_kws[:3])}")
    else:
        # 标题没命中，描述命中也算部分分
        desc_kws = [kw for kw in _all_title_kws() if kw.lower() in blob.lower()]
        if desc_kws:
            score += SCORE_WEIGHTS["title_exact"] * 0.45
            reasons.append(f"JD描述命中相关词：{'、'.join(desc_kws[:3])}")

    # 2) 命中用户选定方向（加分）
    dir_hits = []
    for dname, kws in DIRECTIONS.items():
        for kw in kws:
            if kw.lower() in f"{title} {desc}".lower():
                dir_hits.append(dname)
                break
    if dir_hits:
        score += SCORE_WEIGHTS["direction_bonus"]
        reasons.append(f"符合目标方向：{'/'.join(dict.fromkeys(dir_hits))}")

    # 3) 企业性质（外企/央国企/头部民企）
    nature = detect_company_nature(company)
    job.company_nature = nature
    if nature in ("央国企", "外企", "头部民企"):
        score += SCORE_WEIGHTS["company_nature"]
        reasons.append(f"企业性质：{nature}（关键词识别，非官方认证）")
    elif "博士" in desc or "研究院" in company or "大学" in company:
        score += 4
        reasons.append("研究/高校背景，与研究院经历契合")

    # 4) 资历层级匹配
    sen_hits = [k for k in SENIORITY_KEYWORDS if k.lower() in blob.lower()]
    if sen_hits:
        score += SCORE_WEIGHTS["seniority"]
        reasons.append(f"层级/资历契合：{'、'.join(sen_hits[:3])}")

    # 5) 西安本地
    if "西安" in (job.city + job.district + title + desc)[:200]:
        score += SCORE_WEIGHTS["location"]
        reasons.append("西安本地岗位")

    # 6) 信息完整度：薪资可见
    if job.salary and "**" not in job.salary and job.salary != "":
        score += SCORE_WEIGHTS["salary_known"]
        reasons.append("薪资信息公开")

    # 7) 真实采集加分
    if job.verified:
        score += SCORE_WEIGHTS["verified"]

    job.match_score = round(min(score, 100), 1)
    job.match_reasons = reasons[:6]
    return job


def _all_title_kws():
    from .config import ALL_TITLE_KEYWORDS
    return ALL_TITLE_KEYWORDS


def rank(jobs: list, top_n: int = 40) -> list:
    scored = [score_job(j) for j in jobs]
    scored.sort(key=lambda j: (-j.match_score, j.company))
    return scored[:top_n]


def grade(score: float) -> str:
    if score >= 75:
        return "A · 高度匹配"
    if score >= 60:
        return "B · 较匹配"
    if score >= 45:
        return "C · 可关注"
    return "D · 低相关"
