"""公告查看接口。

公告是全员可读的数据：员工和经理都通过这里的接口查看列表与详情。
发布、编辑、删除属于经理权限，放在 app/routers/manager.py 中单独实现。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.notice import Notice
from app.models.user import User
from app.schemas.notice import NoticeRead


router = APIRouter()


def _to_read(notice: Notice) -> NoticeRead:
    """转换为包含发布人姓名的公告响应。

    数据库只保存 author_id，页面需要显示发布人姓名，
    所以在这里统一把关联对象转换成 author_name 字段。
    """

    return NoticeRead(
        id=notice.id,
        title=notice.title,
        content=notice.content,
        author_id=notice.author_id,
        author_name=notice.author.name if notice.author else None,
        created_at=notice.created_at,
    )


@router.get("", response_model=list[NoticeRead])
def get_notices(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NoticeRead]:
    """登录用户查看公告列表，员工和经理均可访问。

    这里使用 get_current_user 而不是 require_manager：
    只要登录成功就能看公告，但未登录的请求会被直接拦截。
    """

    # joinedload 一次性取出发布人，避免公告列表出现 N+1 查询。
    notices = db.scalars(
        select(Notice)
        .options(joinedload(Notice.author))
        .order_by(Notice.created_at.desc())
    ).all()
    return [_to_read(notice) for notice in notices]


@router.get("/{notice_id}", response_model=NoticeRead)
def get_notice_detail(
    notice_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoticeRead:
    """登录用户查看公告详情，员工和经理均可访问。"""

    notice = db.scalar(
        select(Notice)
        .options(joinedload(Notice.author))
        .where(Notice.id == notice_id)
    )
    if notice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公告不存在",
        )
    return _to_read(notice)
