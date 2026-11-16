"""员工考勤打卡与个人考勤记录接口。"""

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import require_employee
from app.database import get_db
from app.models.attendance import Attendance
from app.models.user import User
from app.schemas.attendance import (
    AttendanceCheckResponse,
    AttendanceRead,
)


router = APIRouter()

# 公司规定的工作时间。集中定义常量，后续调整时间只需要改这里。
WORK_START = time(9, 0)
WORK_END = time(18, 0)


def _month_bounds(month: str | None) -> tuple[str, date, date]:
    """把 YYYY-MM 转换为该月的起止日期范围。"""

    now = datetime.now()
    if month is None:
        year, month_number = now.year, now.month
    else:
        parsed = datetime.strptime(month, "%Y-%m")
        year, month_number = parsed.year, parsed.month

    # 使用“起始日 <= date < 下月起始日”的半开区间，
    # 避免手动计算当月最后一天，也能正确处理 28/29/30/31 天月份。
    start = date(year, month_number, 1)
    if month_number == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month_number + 1, 1)
    return f"{year:04d}-{month_number:02d}", start, end


def _calculate_status(
    check_in: time | None,
    check_out: time | None,
) -> str:
    """根据上下班打卡时间计算考勤状态。"""

    # 只要缺少任意一次打卡，就属于缺卡，不能计算完整出勤结果。
    if check_in is None or check_out is None:
        return "missing"
    if check_in <= WORK_START and check_out >= WORK_END:
        return "normal"
    if check_in > WORK_START and check_out >= WORK_END:
        return "late"
    if check_in <= WORK_START and check_out < WORK_END:
        return "early"
    return "late_early"


def _to_read(
    record: Attendance,
    current_user: User | None = None,
) -> AttendanceRead:
    """把 ORM 考勤记录转换为包含姓名、部门的响应模型。"""

    # 员工本人接口可以直接传 current_user，经理接口则使用 joinedload 加载的 record.user。
    owner = current_user or record.user
    return AttendanceRead(
        id=record.id,
        user_id=record.user_id,
        user_name=owner.name if owner else None,
        department=owner.department if owner else None,
        date=record.date,
        check_in=record.check_in,
        check_out=record.check_out,
        status=record.status,
        remark=record.remark,
        created_at=record.created_at,
    )


@router.post("/check-in", response_model=AttendanceCheckResponse)
def check_in(
    current_user: User = Depends(require_employee),
    db: Session = Depends(get_db),
) -> AttendanceCheckResponse:
    """上班打卡：当天没有记录时创建，已有上班卡时拒绝重复打卡。"""

    now = datetime.now()
    today = now.date()
    check_in_time = now.time().replace(microsecond=0)

    record = db.scalar(
        select(Attendance)
        .options(joinedload(Attendance.user))
        .where(
            Attendance.user_id == current_user.id,
            Attendance.date == today,
        )
    )

    if record is None:
        record = Attendance(
            user_id=current_user.id,
            date=today,
            check_in=check_in_time,
            status="missing",
        )
        db.add(record)
    elif record.check_in is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="今日已完成上班打卡",
        )
    else:
        record.check_in = check_in_time
        record.status = _calculate_status(record.check_in, record.check_out)

    db.commit()
    # 提交后刷新，确保 id、created_at 等数据库生成的值可以返回给前端。
    db.refresh(record)
    return AttendanceCheckResponse(
        message="上班打卡成功",
        data=_to_read(record, current_user),
    )


@router.post("/check-out", response_model=AttendanceCheckResponse)
def check_out(
    current_user: User = Depends(require_employee),
    db: Session = Depends(get_db),
) -> AttendanceCheckResponse:
    """下班打卡：必须已经完成上班打卡。"""

    now = datetime.now()
    today = now.date()
    check_out_time = now.time().replace(microsecond=0)

    record = db.scalar(
        select(Attendance)
        .options(joinedload(Attendance.user))
        .where(
            Attendance.user_id == current_user.id,
            Attendance.date == today,
        )
    )
    if record is None or record.check_in is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先进行上班打卡",
        )
    if record.check_out is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="今日已完成下班打卡",
        )

    record.check_out = check_out_time
    # 下班打卡完成后才具备计算最终状态的两个时间点。
    record.status = _calculate_status(record.check_in, record.check_out)
    db.commit()
    db.refresh(record)
    return AttendanceCheckResponse(
        message="下班打卡成功",
        data=_to_read(record, current_user),
    )


@router.get("/my", response_model=list[AttendanceRead])
def get_my_attendance(
    month: str | None = Query(
        default=None,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="月份，格式 YYYY-MM，不传则查询当前月",
    ),
    current_user: User = Depends(require_employee),
    db: Session = Depends(get_db),
) -> list[AttendanceRead]:
    """员工按月份查询自己的考勤记录。"""

    _, start, end = _month_bounds(month)
    records = db.scalars(
        select(Attendance)
        .options(joinedload(Attendance.user))
        .where(
            Attendance.user_id == current_user.id,
            Attendance.date >= start,
            Attendance.date < end,
        )
        .order_by(Attendance.date.desc())
    ).all()
    return [_to_read(record) for record in records]


@router.get("/today", response_model=AttendanceRead | None)
def get_today_attendance(
    current_user: User = Depends(require_employee),
    db: Session = Depends(get_db),
) -> AttendanceRead | None:
    """员工查询今日考勤，尚未打卡时返回 null。"""

    record = db.scalar(
        select(Attendance)
        .options(joinedload(Attendance.user))
        .where(
            Attendance.user_id == current_user.id,
            Attendance.date == date.today(),
        )
    )
    return _to_read(record) if record is not None else None
