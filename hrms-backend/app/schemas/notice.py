"""公告相关 Pydantic 模型。

发布和编辑分开定义：发布时标题、正文必填，编辑时可以只改其中一项。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoticeCreate(BaseModel):
    """发布公告请求。"""

    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10000)


class NoticeUpdate(BaseModel):
    """编辑公告请求。"""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=10000)


class NoticeRead(BaseModel):
    """公告响应。"""

    id: int
    title: str
    content: str
    author_id: int
    author_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
