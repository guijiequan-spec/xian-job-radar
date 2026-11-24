"""把本地生成的产物同步到 GitHub（通过 REST API，绕开不可用的 git push）。

上传文件清单：index.html、README.md、data/latest.json、data/history.json、
data/daily/当日.json、src/ 下所有源码。
若 token 后续补了 workflow scope，会自动上传 .github/workflows/daily.yml。
"""

import os
import base64
import json
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
from urllib.parse import quote

REPO = "guijiequan-spec/xian-job-radar"
BRANCH = "main"
ROOT = os.path.dirname(os.path.abspath(__file__))
TOKEN = subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def api_request(method, path, body=None, retries=2):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "xian-job-radar-sync",
        },
    )
    last_err = None
    for i in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 404 and method == "GET":
                return None
            last_err = e
            if e.code >= 500:
                continue
            raise
        except Exception as e:  # noqa: BLE001
            last_err = e
            if i < retries:
                import time
                time.sleep(1.5 * (i + 1))
    raise last_err


def get_sha(path):
    return api_request("GET", f"/repos/{REPO}/contents/{quote(path)}?ref={BRANCH}")


def upload_file(rel_path, full_path):
    existing = get_sha(rel_path)
    content = base64.b64encode(open(full_path, "rb").read()).decode("ascii")
    payload = {
        "message": f"chore: 每日数据更新 {datetime.now().strftime('%Y-%m-%d %H:%M')} - {rel_path}",
        "content": content,
        "branch": BRANCH,
    }
    if existing and isinstance(existing, dict) and "sha" in existing:
        payload["sha"] = existing["sha"]
    result = api_request("PUT", f"/repos/{REPO}/contents/{quote(rel_path)}", payload)
    return result.get("content", {}).get("sha", "")[:8]


def collect_upload_files():
    """返回 (相对路径, 绝对路径) 列表。"""
    files = []

    # 顶层产物
    for name in ("index.html", "README.md"):
        p = os.path.join(ROOT, name)
        if os.path.exists(p):
            files.append((name, p))

    # 数据文件
    data_dir = os.path.join(ROOT, "data")
    for fn in ("latest.json", "history.json"):
        p = os.path.join(data_dir, fn)
        if os.path.exists(p):
            files.append((f"data/{fn}", p))
    today = datetime.now().strftime("%Y-%m-%d")
    daily_dir = os.path.join(data_dir, "daily")
    if os.path.isdir(daily_dir):
        for fn in sorted(os.listdir(daily_dir)):
            if fn.startswith(today) and fn.endswith((".json", ".md")):
                files.append((f"data/daily/{fn}", os.path.join(daily_dir, fn)))

    # 源码
    src_dir = os.path.join(ROOT, "src")
    for dirpath, dirnames, filenames in os.walk(src_dir):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if fn.endswith(".py"):
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ROOT).replace("\\", "/")
                files.append((rel, full))

    # workflow（若 token 有权限则上传）
    wf = os.path.join(ROOT, ".github", "workflows", "daily.yml")
    if os.path.exists(wf):
        files.append((".github/workflows/daily.yml", wf))

    return files


def main():
    files = collect_upload_files()
    print(f"待同步 {len(files)} 个文件到 {REPO}")
    ok, fail = 0, []
    for rel, full in files:
        try:
            sha = upload_file(rel, full)
            print(f"  ✅ {rel} ({sha})")
            ok += 1
        except Exception as e:  # noqa: BLE001
            msg = f"{type(e).__name__}: {e}"
            print(f"  ❌ {rel} -> {msg[:100]}")
            fail.append((rel, msg))
    print(f"\n同步完成：{ok}/{len(files)} 成功")
    if fail:
        # workflow 权限不足是已知情况，不算致命失败
        real_fail = [f for f in fail if "workflow" not in f[0]]
        if real_fail:
            print("⚠️ 有文件同步失败：", [f[0] for f in real_fail])
    print(f"永久链接：https://{REPO.split('/')[0]}.github.io/{REPO.split('/')[1]}/")


if __name__ == "__main__":
    main()
