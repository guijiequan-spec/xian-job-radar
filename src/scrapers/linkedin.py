"""领英（LinkedIn）适配器。

说明：领英已于 2023 年关闭中国本土求职服务（InCareer），
中国大陆用户无法通过领英投递国内岗位；国际站访问需相应网络环境。
本适配器如实留痕这一事实，不虚构岗位。
"""

from ..models import SourceResult


def collect(keywords: list) -> SourceResult:
    return SourceResult(
        source="linkedin",
        source_name="领英 LinkedIn",
        status="blocked",
        note=(
            "领英已于 2023 年 8 月关闭中国本土求职服务（InCareer），"
            "国内岗位无法通过领英投递；如需外企机会，建议改用其官网招聘页或猎聘/智联外企专区。"
        ),
    )
