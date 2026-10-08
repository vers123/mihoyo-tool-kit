"""米游社新闻数据模型（O11）

用 Pydantic v2 定义 NewsItem，作为 api_client / storage / excel_writer /
feed 之间统一的数据契约，提供字段验证与类型安全。

api_client._extract_items 用 NewsItem.model_validate 解析响应后 model_dump
返回 dict，对外接口不变（storage/excel 仍接收 dict），但新增了字段验证。
"""

from pydantic import BaseModel, ConfigDict


class NewsItem(BaseModel):
    """单条米游社新闻（与 content_v2_user 响应解析后字段一致）"""

    model_config = ConfigDict(extra="ignore")  # 忽略响应中多余字段

    iInfoId: str
    sTitle: str
    date: str = ""
    sCategoryName: str = ""
    sIntro: str = ""
    poster_url: str = ""
    url: str = ""
