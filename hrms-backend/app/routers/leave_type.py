"""请假类型维护接口。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_employee, require_manager
from app.database import get_db
from app.models.leave_type import LeaveType
from app.schemas.leave_type import (
    LeaveTypeCreate,
    LeaveTypeRead,
    LeaveTypeUpdate,
)


router = APIRouter()
manager_router = APIRouter()


def _ensure_unique(
    db: Session,
    code: str | None,
    name: str | None,
    exclude_id: int | None = None,
) -> None:
    """校验类型代码和名称唯一，给前端返回明确提示。"""

    if code is not None:
        statement = select(LeaveType).where(LeaveType.code == code)
        if exclude_id is not None:
            statement = statement.where(LeaveType.id != exclude_id)
        if db.scalar(statement) is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请假类型代码已存在",
            )

    if name is not None:
        statement = select(LeaveType).where(LeaveType.name == name)
        if exclude_id is not None:
            statement = statement.where(LeaveType.id != exclude_id)
        if db.scalar(statement) is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请假类型名称已存在",
            )


@router.get("", response_model=list[LeaveTypeRead])
def get_active_leave_types(
    _: object = Depends(require_employee),
    db: Session = Depends(get_db),
) -> list[LeaveTypeRead]:
    """员工获取启用中的请假类型。"""

    records = db.scalars(
        select(LeaveType)
        .where(LeaveType.is_active.is_(True))
        .order_by(LeaveType.id.asc())
    ).all()
    return [LeaveTypeRead.model_validate(record) for record in records]


@manager_router.get("", response_model=list[LeaveTypeRead])
def get_leave_types(
    _: object = Depends(require_manager),
    db: Session = Depends(get_db),
) -> list[LeaveTypeRead]:
    """经理查询全部请假类型。"""

    records = db.scalars(
        select(LeaveType).order_by(LeaveType.id.asc())
    ).all()
    return [LeaveTypeRead.model_validate(record) for record in records]


@manager_router.post("", response_model=LeaveTypeRead)
def create_leave_type(
    payload: LeaveTypeCreate,
    _: object = Depends(require_manager),
    db: Session = Depends(get_db),
) -> LeaveTypeRead:
    """经理新增请假类型。"""

    _ensure_unique(db, payload.code, payload.name)
    record = LeaveType(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return LeaveTypeRead.model_validate(record)


@manager_router.put("/{leave_type_id}", response_model=LeaveTypeRead)
def update_leave_type(
    leave_type_id: int,
    payload: LeaveTypeUpdate,
    _: object = Depends(require_manager),
    db: Session = Depends(get_db),
) -> LeaveTypeRead:
    """经理编辑或停用请假类型，不物理删除已被引用的数据。"""

    record = db.get(LeaveType, leave_type_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="请假类型不存在",
        )

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有需要修改的内容",
        )
    _ensure_unique(
        db,
        update_data.get("code"),
        update_data.get("name"),
        exclude_id=leave_type_id,
    )

    for field, value in update_data.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return LeaveTypeRead.model_validate(record)
