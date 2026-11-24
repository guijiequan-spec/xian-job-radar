"""轻量 HTTP 工具：仅用标准库，带超时、UA、重试、robots 基础检查。"""

import ssl
import time
import urllib.request
import urllib.error
import urllib.robotparser
from typing import Optional

from ..config import USER_AGENT, REQUEST_TIMEOUT

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

_LAST_REQUEST = {}


def get(url: str, referer: str = "", delay: float = 0.0, retries: int = 2) -> Optional[str]:
    """GET 返回文本；失败返回 None。delay>0 时对同域名做礼貌间隔。"""
    if delay > 0:
        from urllib.parse import urlparse
        host = urlparse(url).netloc
        elapsed = time.time() - _LAST_REQUEST.get(host, 0)
        if elapsed < delay:
            time.sleep(delay - elapsed)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    }
    if referer:
        headers["Referer"] = referer
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=_CTX) as resp:
                raw = resp.read()
                charset = "utf-8"
                ct = resp.headers.get("Content-Type", "")
                if "gbk" in ct.lower() or "gb2312" in ct.lower():
                    charset = "gbk"
                try:
                    text = raw.decode(charset)
                except UnicodeDecodeError:
                    text = raw.decode("utf-8", errors="ignore")
                from urllib.parse import urlparse
                _LAST_REQUEST[urlparse(url).netloc] = time.time()
                return text
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
    print(f"  [http] GET failed {url[:90]} -> {type(last_err).__name__}: {str(last_err)[:80]}")
    return None


def robots_allowed(base_url: str, path: str = "/") -> bool:
    """保守 robots 检查：取不到或解析异常时返回 False（默认禁止）。"""
    try:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(base_url.rstrip("/") + "/robots.txt")
        rp.read()
        return rp.can_fetch(USER_AGENT, base_url.rstrip("/") + path)
    except Exception:
        return False
