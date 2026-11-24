"""BOSS 直聘公开页采集适配器。

BOSS 直聘搜索页强依赖登录态与 JS，且 robots 严格。
本适配器默认保守：robots 不允许则跳过并留痕，不尝试绕过登录/验证码。
保留接口，若将来有合法授权通道可在此接入。
"""

from ..models import SourceResult
from .http import robots_allowed

BASE = "https://www.zhipin.com"


def collect(keywords: list, enabled: bool = False) -> SourceResult:
    result = SourceResult(source="boss", source_name="BOSS直聘")
    if not enabled:
        result.status = "blocked"
        result.note = "BOSS 直聘搜索需登录态且 robots 严格，默认不采集；如日后有合法授权通道可开启 enabled"
        return result
    if not robots_allowed(BASE, "/web/geek/job"):
        result.status = "blocked"
        result.error = "robots.txt 不允许抓取 /web/geek/job"
        return result
    result.status = "empty"
    result.note = "未配置合法授权会话，跳过"
    return result
