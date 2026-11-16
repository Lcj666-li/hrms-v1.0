"""员工请假申请接口。

本文件只处理“员工自己的请假”：
提交申请、查看自己的记录、撤销尚未审批的申请。
经理审批请假的功能放在 app/routers/manager.py，避免把两种角色的权限混在一起。
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import require_employee
from app.database import get_db
from app.models.leave import LeaveRequest
from app.models.leave_type import LeaveType
from app.models.user import User
from app.schemas.leave import LeaveCancelResponse, LeaveCreate, LeaveRead


router = APIRouter()


def _to_read(record: LeaveRequest) -> LeaveRead:
    """把 ORM 请假记录转换为包含申请人、审批人姓名的响应模型。

    ORM 对象里只有 user_id、approver_id 这类外键数字，
    但页面需要显示“谁请假、谁审批”，所以这里统一在这里拼装响应字段，
    避免每个接口都重复写一遍转换逻辑。
    """

    return LeaveRead(
        id=record.id,
        user_id=record.user_id,
        user_name=record.user.name if record.user else None,
        department=record.user.department if record.user else None,
        leave_type_id=record.leave_type_id,
        leave_type_name=record.leave_type.name if record.leave_type else None,
        leave_type_is_paid=(
            record.leave_type.is_paid if record.leave_type else None
        ),
        start_date=record.start_date,
        end_date=record.end_date,
        reason=record.reason,
        status=record.status,
        approver_id=record.approver_id,
        approver_name=record.approver.name if record.approver else None,
        approve_comment=record.approve_comment,
        approve_time=record.approve_time,
        created_at=record.created_at,
    )


@router.post("", response_model=LeaveRead)
def create_leave(
    payload: LeaveCreate,
    current_user: User = Depends(require_employee),
    db: Session = Depends(get_db),
) -> LeaveRead:
    """员工提交请假申请。

    user_id 取自 JWT 中的当前登录用户，而不是请求体，
    这样员工无法通过改参数替别人提交请假，从源头避免越权。
    需要审批的类型进入 pending；无需审批的类型直接标记为 approved，
    并记录系统自动通过说明，避免请假类型中的审批配置成为无效字段。
    """

    leave_type = db.scalar(
        select(LeaveType).where(
            LeaveType.id == payload.leave_type_id,
            LeaveType.is_active.is_(True),
        )
    )
    if leave_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请假类型不存在或已停用",
        )

    record = LeaveRequest(
        user_id=current_user.id,
        leave_type_id=leave_type.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        status="pending" if leave_type.requires_approval else "approved",
        approve_comment=(
            None
            if leave_type.requires_approval
            else "该请假类型无需审批，系统自动通过"
        ),
        approve_time=(
            None if leave_type.requires_approval else datetime.now()
        ),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_read(record)


@router.get("/my", response_model=list[LeaveRead])
def get_my_leaves(
    leave_status: str | None = Query(
        default=None,
        alias="status",
        pattern=r"^(pending|approved|rejected|cancelled)$",
    ),
    current_user: User = Depends(require_employee),
    db: Session = Depends(get_db),
) -> list[LeaveRead]:
    """员工查看自己的请假记录，可按状态筛选。"""

    # joinedload 会在一条 SQL 里把关联的申请人和审批人一起查出来，
    # 避免列表循环中逐条查询导致的 N+1 性能问题。
    statement = (
        select(LeaveRequest)
        .options(
            joinedload(LeaveRequest.user),
            joinedload(LeaveRequest.leave_type),
            joinedload(LeaveRequest.approver),
        )
        .where(LeaveRequest.user_id == current_user.id)
    )
    if leave_status is not None:
        statement = statement.where(LeaveRequest.status == leave_status)

    records = db.scalars(
        statement.order_by(LeaveRequest.created_at.desc())
    ).all()
    return [_to_read(record) for record in records]


@router.put("/{leave_id}/cancel", response_model=LeaveCancelResponse)
def cancel_leave(
    leave_id: int,
    current_user: User = Depends(require_employee),
    db: Session = Depends(get_db),
) -> LeaveCancelResponse:
    """员工撤销尚未审批的请假申请。

    查询条件同时带上 id 和 user_id：即使员工猜到别人的请假 id，
    也查不到记录，只会收到 404，从而看不到也无法操作他人数据。
    """

    record = db.scalar(
        select(LeaveRequest).where(
            LeaveRequest.id == leave_id,
            LeaveRequest.user_id == current_user.id,
        )
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="请假申请不存在",
        )
    if record.status != "pending":
        # 已通过或已驳回的申请代表审批结果已经生效，不允许员工自行撤销。
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有待审批的申请可以撤销",
        )

    record.status = "cancelled"
    db.commit()
    return LeaveCancelResponse(message="请假申请已撤销", id=record.id)
