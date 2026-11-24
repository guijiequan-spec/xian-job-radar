"""GitHub Pages 看板首页生成。

把最新数据内嵌进 HTML（而非运行时 fetch），避免 GitHub Pages 的缓存/CDN 问题，
保证每次推送后打开永久链接即是最新内容。
"""

import json
import html as htmlmod


def _e(s):
    return htmlmod.escape(str(s or ""))


def _grade(score):
    try:
        s = float(score)
    except (TypeError, ValueError):
        s = 0
    if s >= 75:
        return "A", "高度匹配", "badge-a"
    if s >= 60:
        return "B", "较匹配", "badge-b"
    if s >= 45:
        return "C", "可关注", "badge-c"
    return "D", "低相关", "badge-d"


def _job_card(j: dict, is_new: bool = False) -> str:
    letter, label, cls = _grade(j.get("match_score", 0))
    title = _e(j.get("title", ""))
    url = j.get("url", "")
    company = _e(j.get("company", ""))
    nature = _e(j.get("company_nature", "未识别"))
    city = _e((j.get("city", "") + " " + j.get("district", "")).strip())
    exp = _e(j.get("experience", "") or "—")
    edu = _e(j.get("education", "") or "—")
    salary = j.get("salary", "")
    salary = _e(salary) if salary and "**" not in salary else "面议/未公开"
    verified = "✅ 实采" if j.get("verified") else "⚠️ 索引线索"
    new_tag = '<span class="new-tag">NEW</span>' if is_new else ""
    title_html = f'<a href="{_e(url)}" target="_blank" rel="noopener">{title}</a>' if url else title
    reasons = j.get("match_reasons", []) or []
    reasons_html = "".join(f"<li>{_e(r)}</li>" for r in reasons[:4])

    nature_cls = {"央国企": "nature-soe", "外企": "nature-foreign", "头部民企": "nature-private"}.get(j.get("company_nature", ""), "nature-other")

    return f"""
    <div class="job-card">
      <div class="job-head">
        <div class="job-title">{title_html} {new_tag}</div>
        <div class="score {cls}"><b>{letter}</b> {j.get('match_score', 0):.0f}</div>
      </div>
      <div class="job-meta">
        <span class="nature {nature_cls}">{nature}</span>
        <span>🏢 {company}</span>
        <span>📍 {city}</span>
        <span>💰 {salary}</span>
        <span>🎓 {exp} / {edu}</span>
        <span class="src">🔗 {_e(j.get('source_name',''))} · {verified}</span>
      </div>
      <ul class="reasons">{reasons_html}</ul>
    </div>"""


def _source_rows(sources):
    status_cn = {"success": "✅ 正常", "blocked": "⛔ 受限", "error": "❌ 失败", "empty": "⚠️ 空"}
    rows = []
    for s in sources:
        note = s.get("note") or s.get("error") or ""
        rows.append(
            f"<tr><td>{_e(s.get('source_name',''))}</td>"
            f"<td>{status_cn.get(s.get('status',''), s.get('status',''))}</td>"
            f"<td>{s.get('count', 0)}</td><td>{_e(note)}</td></tr>"
        )
    return "".join(rows)


def build_index_html(latest: dict) -> str:
    new_keys = {j.get("key") or (j.get("company", "") + "|" + j.get("title", "")) for j in latest.get("new_jobs", [])}
    jobs = latest.get("jobs", [])
    new_count = latest.get("new_count", 0)

    cards_new = "".join(_job_card(j, is_new=True) for j in latest.get("new_jobs", []))
    if not cards_new:
        cards_new = '<div class="empty">本轮无新增岗位（首次运行或暂无新职位）</div>'

    cards_all = "".join(_job_card(j) for j in jobs[:60])
    if not cards_all:
        cards_all = '<div class="empty">暂无岗位数据</div>'

    src_rows = _source_rows(latest.get("sources", []))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>西安岗位雷达 · 每日更新</title>
<style>
  :root {{
    --bg:#f6f7f9; --card:#fff; --ink:#1f2329; --sub:#646a73; --line:#e5e6eb;
    --brand:#2b5aed; --brand-soft:#eaf0ff; --red:#d92b2b; --green:#0a9e5c;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif; line-height:1.6; }}
  .wrap {{ max-width:960px; margin:0 auto; padding:28px 18px 60px; }}
  header {{ background:linear-gradient(120deg,#1d3fa8,#2b5aed); color:#fff; border-radius:16px;
    padding:30px 28px; box-shadow:0 8px 24px rgba(43,90,237,.18); }}
  header h1 {{ margin:0 0 6px; font-size:26px; }}
  header .sub {{ opacity:.9; font-size:14px; }}
  .stats {{ display:flex; flex-wrap:wrap; gap:12px; margin-top:20px; }}
  .stat {{ background:rgba(255,255,255,.15); border-radius:10px; padding:12px 18px; min-width:110px; }}
  .stat b {{ display:block; font-size:24px; }}
  .stat span {{ font-size:12px; opacity:.85; }}
  .section {{ margin-top:32px; }}
  .section h2 {{ font-size:19px; margin:0 0 4px; display:flex; align-items:center; gap:8px; }}
  .section .hint {{ color:var(--sub); font-size:13px; margin:0 0 16px; }}
  .job-card {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
    padding:16px 18px; margin-bottom:12px; transition:.15s; }}
  .job-card:hover {{ box-shadow:0 4px 16px rgba(0,0,0,.07); border-color:#c9d4f5; }}
  .job-head {{ display:flex; justify-content:space-between; gap:12px; align-items:flex-start; }}
  .job-title {{ font-size:16px; font-weight:600; }}
  .job-title a {{ color:var(--brand); text-decoration:none; }}
  .job-title a:hover {{ text-decoration:underline; }}
  .score {{ white-space:nowrap; font-size:13px; padding:3px 10px; border-radius:20px; font-weight:600; }}
  .score b {{ font-size:15px; }}
  .badge-a {{ background:#fdecec; color:var(--red); }}
  .badge-b {{ background:#fff3e0; color:#c77700; }}
  .badge-c {{ background:#eaf0ff; color:var(--brand); }}
  .badge-d {{ background:#f2f3f5; color:var(--sub); }}
  .new-tag {{ background:var(--red); color:#fff; font-size:10px; padding:2px 6px;
    border-radius:4px; vertical-align:middle; margin-left:6px; }}
  .job-meta {{ display:flex; flex-wrap:wrap; gap:8px 16px; margin-top:10px;
    font-size:12.5px; color:var(--sub); }}
  .nature {{ padding:1px 8px; border-radius:4px; font-weight:600; }}
  .nature-soe {{ background:#fdecec; color:var(--red); }}
  .nature-foreign {{ background:#eaf0ff; color:var(--brand); }}
  .nature-private {{ background:#e8f8f0; color:var(--green); }}
  .nature-other {{ background:#f2f3f5; color:var(--sub); }}
  .src {{ width:100%; }}
  .reasons {{ margin:10px 0 0; padding-left:18px; font-size:12.5px; color:#4e5359; }}
  .reasons li {{ margin:2px 0; }}
  .empty {{ color:var(--sub); padding:24px; text-align:center; background:var(--card);
    border:1px dashed var(--line); border-radius:12px; }}
  table {{ width:100%; border-collapse:collapse; background:var(--card);
    border-radius:12px; overflow:hidden; font-size:13px; }}
  th,td {{ padding:10px 12px; text-align:left; border-bottom:1px solid var(--line); }}
  th {{ background:#f2f4f7; font-weight:600; }}
  td:last-child {{ color:var(--sub); }}
  footer {{ margin-top:40px; text-align:center; color:var(--sub); font-size:12px; }}
  code {{ background:#eef0f3; padding:1px 5px; border-radius:4px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>西安岗位雷达</h1>
    <div class="sub">外企 · 央国企 · 头部民企 ｜ 按个人简历智能匹配 ｜ 数据更新于 {_e(latest.get('generated_at',''))}</div>
    <div class="stats">
      <div class="stat"><b>{latest.get('total', 0)}</b><span>本轮岗位</span></div>
      <div class="stat"><b>{new_count}</b><span>本次新增</span></div>
      <div class="stat"><b>{latest.get('grade_a', 0)}</b><span>高度匹配 A</span></div>
      <div class="stat"><b>{latest.get('grade_b', 0)}</b><span>较匹配 B</span></div>
      <div class="stat"><b>{latest.get('history_count', 0)}</b><span>累计去重</span></div>
    </div>
  </header>

  <div class="section">
    <h2>🆕 本次新增岗位 <span style="font-size:13px;color:var(--sub);font-weight:400">({new_count})</span></h2>
    <p class="hint">相对历史库本次新出现的岗位，优先查看。</p>
    {cards_new}
  </div>

  <div class="section">
    <h2>🏆 全部高匹配岗位</h2>
    <p class="hint">按匹配分排序，取前 60 条。点击标题跳转原始招聘页核实时效性。</p>
    {cards_all}
  </div>

  <div class="section">
    <h2>📡 数据源状态</h2>
    <p class="hint">失败与受限均如实记录，不虚构岗位。</p>
    <table>
      <tr><th>数据源</th><th>状态</th><th>采集数</th><th>说明</th></tr>
      {src_rows}
    </table>
  </div>

  <div class="section">
    <h2>ℹ️ 数据说明</h2>
    <p class="hint" style="line-height:1.9">
      · 仅采集公开可访问的雇主招聘信息（JD），不涉及个人隐私。<br>
      · 薪资显示 <code>**-**元</code> 为平台未登录打码，如实记录不做推测。<br>
      · 企业性质为关键词识别打标，非官方认证。<br>
      · 搜索引擎来源标注为索引线索，不计入正式岗位表。<br>
      · 领英中国求职服务已于 2023 年关闭，不作投递渠道。<br>
      · 历史去重库记录每个岗位首次/最近出现日期，用于识别"每日新增"。
    </p>
  </div>

  <footer>本页由 GitHub Pages 托管，随每日采集自动更新 · 岗位以原始页面为准</footer>
</div>
</body>
</html>"""
