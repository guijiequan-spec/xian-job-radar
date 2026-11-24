"""西安岗位雷达 · 主入口。

流程：多源采集 -> 去重 -> 匹配评分 -> 历史对比 -> 落盘 -> 生成 README
"""

import os
import sys
import json
from datetime import datetime

# 保证从仓库根目录运行时可 import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import SEARCH_QUERIES
from src.models import Job, SourceResult, dedup, save_json
from src.matcher import rank
from src.reporter import write_outputs
from src.scrapers import zhilian, liepin, boss, linkedin, search

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_PATH = os.path.join(ROOT, "data", "history.json")


def load_history() -> dict:
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"=== 西安岗位雷达 {today} ===")

    # 1) 多源采集（各源独立容错）
    source_results = []
    collectors = [
        ("智联招聘", lambda: zhilian.collect(SEARCH_QUERIES)),
        ("猎聘", lambda: liepin.collect(SEARCH_QUERIES)),
        ("BOSS直聘", lambda: boss.collect(SEARCH_QUERIES, enabled=False)),
        ("领英", lambda: linkedin.collect(SEARCH_QUERIES)),
        ("搜索引擎聚合", lambda: search.collect(SEARCH_QUERIES)),
    ]
    for name, fn in collectors:
        print(f"\n[{name}] 开始采集...")
        try:
            r = fn()
        except Exception as e:  # noqa: BLE001
            r = SourceResult(source=name, source_name=name, status="error", error=f"{type(e).__name__}: {e}")
        source_results.append(r)
        print(f"[{name}] 状态={r.status} 采集={len(r.jobs)} 条")

    # 搜索引擎来源为未验证的索引摘要，不作为正式岗位进入排名表（避免搜索页标题混入岗位）
    all_jobs = [j for r in source_results if r.source != "search" for j in r.jobs]
    jobs = dedup(all_jobs)
    leads = dedup([j for r in source_results if r.source == "search" for j in r.jobs])
    print(f"\n去重后岗位总数：{len(jobs)}")

    # 2) 匹配评分 + 排序
    ranked = rank(jobs, top_n=60)
    print(f"评分完成，Top1：{ranked[0].title if ranked else '无'} / {ranked[0].match_score if ranked else 0}")

    # 3) 历史对比（新增岗位）
    history = load_history()
    new_keys = set()
    for j in ranked:
        if j.key not in history:
            new_keys.add(j.key)
            history[j.key] = {"first_seen": today, "title": j.title, "company": j.company}
    # 更新 last_seen
    for j in ranked:
        if j.key in history:
            history[j.key]["last_seen"] = today
    save_json(HISTORY_PATH, history)

    # 4) 落盘 + README
    write_outputs(ROOT, ranked, source_results, today, new_keys, len(history), leads=leads)
    print(f"\n完成：新增 {len(new_keys)} 条，累计 {len(history)} 条")
    print(f"README: {os.path.join(ROOT, 'README.md')}")


if __name__ == "__main__":
    main()
