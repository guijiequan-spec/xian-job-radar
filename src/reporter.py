"""报告生成：README.md（永久展示）+ 当日 JSON + 变更对比。"""

import os
from datetime import datetime
from .matcher import grade
from .models import save_json
from .target_companies import TARGET_COMPANIES, company_search_links

NATURE_ORDER = {"央国企": 0, "外企": 1, "头部民企": 2, "其他": 3, "未识别": 4}


def _md_escape(s):
    return str(s or "").replace("|", "｜").replace("\n", " ").strip()


def build_daily_md(jobs, source_results, today, new_keys):
    """当日 Markdown 报告。"""
    lines = [f"# 西安岗位雷达 · {today} 日报", ""]
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} ｜ 共采集 {len(jobs)} 条岗位 ｜ 新增 {len(new_keys)} 条")
    lines.append("")
    lines.append("## 一、数据源状态（失败如实留痕）")
    lines.append("")
    lines.append("| 数据源 | 状态 | 采集数 | 说明 |")
    lines.append("|---|---|---|---|")
    status_cn = {"success": "✅ 成功", "blocked": "⛔ 受限", "error": "❌ 失败", "empty": "⚠️ 空"}
    for r in source_results:
        lines.append(f"| {r.source_name} | {status_cn.get(r.status, r.status)} | {len(r.jobs)} | {_md_escape(r.note or r.error)} |")
    lines.append("")
    lines.append("## 二、今日新增岗位（相对昨日）")
    lines.append("")
    top = [j for j in jobs if j.key in new_keys][:30]
    if top:
        lines.append("| 匹配 | 岗位 | 公司 | 性质 | 地点 | 链接 |")
        lines.append("|---|---|---|---|---|---|")
        for j in top:
            g = grade(j.match_score).split(" · ")[0]
            lines.append(
                f"| {g}/{j.match_score:.0f} | {_md_escape(j.title)} | {_md_escape(j.company)} | "
                f"{j.company_nature} | {_md_escape(j.city + j.district)} | [查看]({j.url}) |"
            )
    else:
        lines.append("_今日无新增岗位（或为首次运行）。_")
    lines.append("")
    lines.append("## 三、数据说明")
    lines.append("")
    lines.append("- 岗位来自各平台**公开可访问**页面，仅采集雇主侧 JD，不采集任何个人隐私信息。")
    lines.append("- `verified=False` 的条目来自搜索引擎公开索引摘要，字段可能不完整，请以原页面为准。")
    lines.append("- 薪资显示 `**-**元` 是平台未登录打码，如实记录，未做任何推测填充。")
    lines.append("- 企业性质为关键词识别打标，非官方认证，仅供筛选参考。")
    return "\n".join(lines)


def build_readme(jobs, source_results, today, history_count, leads=None):
    """生成 GitHub 仓库首页 README（永久展示页）。"""
    top = jobs[:50]
    a_cnt = sum(1 for j in jobs if j.match_score >= 75)
    b_cnt = sum(1 for j in jobs if 60 <= j.match_score < 75)

    lines = [
        "# 西安岗位雷达 · 每日自动更新",
        "",
        "> 面向权贵杰个人简历画像，聚焦西安地区外企 / 央国企 / 头部民企岗位，每日自动采集与匹配。",
        "",
        f"**最近更新**：{today} ｜ **累计去重岗位**：{history_count} 条 ｜ **本次采集**：{len(jobs)} 条 ｜ **高度匹配(A)**：{a_cnt} 条 ｜ **较匹配(B)**：{b_cnt} 条",
        "",
        "## 匹配画像",
        "",
        "- 15年HR管理 + 港股上市招聘平台（猎聘）大数据研究院副院长",
        "- 中国人民大学人力资源管理博士 + 高级经济师（副高）+ 中共党员",
        "- 目标方向：政企合作/公共事务 · HRD/人力资源总监 · 行业研究/战略",
        "- 目标城市：西安 ｜ 目标企业：外企 · 央国企 · 头部民企",
        "",
        "## 本次高匹配岗位（按匹配分排序）",
        "",
        "| 匹配 | 岗位 | 公司 | 性质 | 地点 | 经验/学历 | 来源 |",
        "|---|---|---|---|---|---|---|",
    ]
    for j in top:
        g = grade(j.match_score).split(" · ")[0]
        salary = j.salary if j.salary and "**" not in j.salary else "—"
        exp = j.experience or "—"
        edu = j.education or "—"
        link = f"[链接]({j.url})" if j.url else "—"
        title_cell = f"[{_md_escape(j.title)}]({j.url})" if j.url else _md_escape(j.title)
        lines.append(
            f"| {g}/{j.match_score:.0f} | {title_cell} | {_md_escape(j.company)} | "
            f"{j.company_nature} | {_md_escape(j.city + j.district)} | {exp}/{edu} | {j.source_name} |"
        )
    if not top:
        lines.append("| — | _本次未采集到岗位_ | — | — | — | — | — |")

    # 目标企业直达区（用户的重点目标：外企/央国企/头部民企）
    lines += [
        "",
        "## 西安目标企业直达（外企 / 央国企 / 头部民企）",
        "",
        "> 以下是西安地区目标企业的招聘检索直达入口。公开搜索未必抓到其在招岗位，点击可直接进入该企业的实时岗位检索页。",
    ]
    for nature, names in TARGET_COMPANIES.items():
        lines.append("")
        lines.append(f"**{nature}**")
        lines.append("")
        lines.append("| 企业 | 实时岗位检索 |")
        lines.append("|---|---|")
        for name in names:
            lines.append(f"| {name} | {company_search_links(name)} |")

    # 检索线索区（未验证，来自公开搜索索引）
    if leads:
        lines += [
            "",
            "## 更多检索线索（来自公开搜索索引，未验证，非岗位详情）",
            "",
            "> 以下为搜索引擎索引到的招聘信息标题，字段可能不完整且可能已失效，仅供扩展检索，正式岗位请以上方表格为准。",
            "",
            "| 线索标题 | 来源 |",
            "|---|---|",
        ]
        for j in leads[:15]:
            t = _md_escape(j.title)
            if j.url:
                t = f"[{t}]({j.url})"
            lines.append(f"| {t} | {j.source_name} |")

    lines += [
        "",
        "## 数据源状态",
        "",
        "| 数据源 | 状态 | 本次采集 | 备注 |",
        "|---|---|---|---|",
    ]
    status_cn = {"success": "✅ 正常", "blocked": "⛔ 受限", "error": "❌ 失败", "empty": "⚠️ 空"}
    for r in source_results:
        lines.append(f"| {r.source_name} | {status_cn.get(r.status, r.status)} | {len(r.jobs)} | {_md_escape(r.note or r.error)} |")
    lines += [
        "",
        "## 关于数据与合规",
        "",
        "- 仅采集**公开可访问**的雇主招聘信息（JD），不采集简历、姓名、电话等个人隐私。",
        "- 薪资打码 `**-**元` 为平台未登录状态原样展示，不做推测。",
        "- 搜索引擎来源（verified=false）为公开索引摘要，字段可能不完整。",
        "- 企业性质为关键词自动识别，非官方认证。",
        "- 领英中国求职服务已于2023年关闭，故不作为投递渠道。",
        "",
        "## 目录结构",
        "",
        "- `data/daily/YYYY-MM-DD.json` — 每日采集快照（含匹配分与理由）",
        "- `data/history.json` — 历史累计去重岗位库",
        "- `data/daily/YYYY-MM-DD.md` — 每日变更报告",
        "- `src/` — 采集与匹配源码",
        "- `.github/workflows/daily.yml` — 每日定时自动更新",
        "",
        "---",
        "",
        "_本仓库由 GitHub Actions 每日自动更新。岗位以原始链接页面为准，投递前请自行核实时效性。_",
    ]
    return "\n".join(lines)


def write_outputs(root, jobs, source_results, today, new_keys, history_count, leads=None):
    daily_dir = os.path.join(root, "data", "daily")
    os.makedirs(daily_dir, exist_ok=True)

    # 当日 JSON
    save_json(os.path.join(daily_dir, f"{today}.json"), {
        "date": today,
        "total": len(jobs),
        "new_count": len(new_keys),
        "sources": [r.to_dict() for r in source_results],
        "jobs": [j.to_dict() for j in jobs],
    })

    # 当日 Markdown
    with open(os.path.join(daily_dir, f"{today}.md"), "w", encoding="utf-8") as f:
        f.write(build_daily_md(jobs, source_results, today, new_keys))

    # README
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write(build_readme(jobs, source_results, today, history_count, leads=leads))
