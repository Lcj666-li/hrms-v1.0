"""员工薪资查询和经理薪资管理接口。"""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import require_employee, require_manager
from app.database import get_db
from app.models.role import Role
from app.models.salary import SalaryRecord
from app.models.user import User
from app.schemas.salary import SalaryCreate, SalaryRead, SalaryUpdate


router = APIRouter()
manager_router = APIRouter()

MONEY_ZERO = Decimal("0.00")
SALARY_MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"
SALARY_STATUS_PATTERN = r"^(draft|issued)$"


def _calculate_actual_salary(
    base_salary: Decimal,
    attendance_deduction: Decimal,
    leave_deduction: Decimal,
    bonus: Decimal,
    social_security: Decimal,
    tax: Decimal,
) -> Decimal:
    """按统一公式计算实发工资。"""

    actual = (
        base_salary
        + bonus
        - attendance_deduction
        - leave_deduction
        - social_security
        - tax
    )
    return actual.quantize(Decimal("0.01"))


def _to_read(record: SalaryRecord) -> SalaryRead:
    """转换薪资记录并附带员工、部门及制单人信息。"""

    return SalaryRead(
        id=record.id,
        user_id=record.user_id,
        user_name=record.user.name if record.user else None,
        department=record.user.department if record.user else None,
        salary_month=record.salary_month,
        base_salary=record.base_salary,
        attendance_deduction=record.attendance_deduction,
        leave_deduction=record.leave_deduction,
        bonus=record.bonus,
        social_security=record.social_security,
        tax=record.tax,
        actual_salary=record.actual_salary,
        status=record.status,
        created_by=record.created_by,
        created_by_name=record.creator.name if record.creator else None,
        issued_at=record.issued_at,
        created_at=record.created_at,
    )


def _load_employee(db: Session, employee_id: int) -> User:
    """只允许把薪资记录关联到员工角色账号。"""

    employee = db.scalar(
        select(User)
        .options(joinedload(User.department_ref))
        .where(
            User.id == employee_id,
            User.role_ref.has(Role.code == "employee"),
        )
    )
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="员工不存在",
        )
    return employee


def _ensure_salary_not_negative(actual_salary: Decimal) -> None:
    """实发工资不能为负数。"""

    if actual_salary < MONEY_ZERO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="扣款和税费合计不能超过基本工资与奖金之和",
        )


def _ensure_unique_month(
    db: Session,
    user_id: int,
    salary_month: str,
    exclude_id: int | None = None,
) -> None:
    """同一员工同一月份只能有一条薪资记录。"""

    statement = select(SalaryRecord).where(
        SalaryRecord.user_id == user_id,
        SalaryRecord.salary_month == salary_month,
    )
    if exclude_id is not None:
        statement = statement.where(SalaryRecord.id != exclude_id)
    if db.scalar(statement) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该员工在此月份已有薪资记录",
        )


def _record_options() -> tuple:
    """薪资响应需要一次性加载员工、部门和制单人。"""

    return (
        joinedload(SalaryRecord.user).joinedload(User.department_ref),
        joinedload(SalaryRecord.creator),
    )


@router.get("/my", response_model=list[SalaryRead])
def get_my_salary(
    month: str | None = Query(
        default=None,
        pattern=SALARY_MONTH_PATTERN,
        description="月份，格式 YYYY-MM",
    ),
    current_user: User = Depends(require_employee),
    db: Session = Depends(get_db),
) -> list[SalaryRead]:
    """员工只查看本人已经发放的薪资记录。"""

    statement = (
        select(SalaryRecord)
        .options(*_record_options())
        .where(
            SalaryRecord.user_id == current_user.id,
            SalaryRecord.status == "issued",
        )
    )
    if month is not None:
        statement = statement.where(SalaryRecord.salary_month == month)

    records = db.scalars(
        statement.order_by(SalaryRecord.salary_month.desc())
    ).all()
    return [_to_read(record) for record in records]


@manager_router.get("", response_model=list[SalaryRead])
def get_salary_records(
    month: str | None = Query(
        default=None,
        pattern=SALARY_MONTH_PATTERN,
        description="月份，格式 YYYY-MM",
    ),
    user_id: int | None = Query(default=None, gt=0),
    salary_status: str | None = Query(
        default=None,
        alias="status",
        pattern=SALARY_STATUS_PATTERN,
    ),
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> list[SalaryRead]:
    """经理按月份、员工和状态查询薪资记录。"""

    statement = select(SalaryRecord).options(*_record_options())
    if month is not None:
        statement = statement.where(SalaryRecord.salary_month == month)
    if user_id is not None:
        statement = statement.where(SalaryRecord.user_id == user_id)
    if salary_status is not None:
        statement = statement.where(SalaryRecord.status == salary_status)

    records = db.scalars(
        statement.order_by(
            SalaryRecord.salary_month.desc(),
            SalaryRecord.user_id.asc(),
        )
    ).all()
    return [_to_read(record) for record in records]


@manager_router.post("", response_model=SalaryRead)
def create_salary_record(
    payload: SalaryCreate,
    current_manager: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> SalaryRead:
    """经理创建薪资草稿，实发工资由后端统一计算。"""

    _load_employee(db, payload.user_id)
    _ensure_unique_month(db, payload.user_id, payload.salary_month)
    values = payload.model_dump()
    actual_salary = _calculate_actual_salary(
        values["base_salary"],
        values["attendance_deduction"],
        values["leave_deduction"],
        values["bonus"],
        values["social_security"],
        values["tax"],
    )
    _ensure_salary_not_negative(actual_salary)

    record = SalaryRecord(
        **values,
        actual_salary=actual_salary,
        status="draft",
        created_by=current_manager.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    record = db.scalar(
        select(SalaryRecord)
        .options(*_record_options())
        .where(SalaryRecord.id == record.id)
    )
    assert record is not None
    return _to_read(record)


@manager_router.put("/{salary_id}", response_model=SalaryRead)
def update_salary_record(
    salary_id: int,
    payload: SalaryUpdate,
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> SalaryRead:
    """经理编辑尚未发放的薪资草稿。"""

    record = db.scalar(
        select(SalaryRecord)
        .options(*_record_options())
        .where(SalaryRecord.id == salary_id)
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="薪资记录不存在",
        )
    if record.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已发放的薪资记录不能修改",
        )

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有需要修改的内容",
        )

    target_user_id = update_data.get("user_id", record.user_id)
    target_month = update_data.get("salary_month", record.salary_month)
    if target_user_id != record.user_id:
        _load_employee(db, target_user_id)
    if (
        target_user_id != record.user_id
        or target_month != record.salary_month
    ):
        _ensure_unique_month(
            db,
            target_user_id,
            target_month,
            exclude_id=salary_id,
        )

    for field, value in update_data.items():
        setattr(record, field, value)

    record.actual_salary = _calculate_actual_salary(
        record.base_salary,
        record.attendance_deduction,
        record.leave_deduction,
        record.bonus,
        record.social_security,
        record.tax,
    )
    _ensure_salary_not_negative(record.actual_salary)

    db.commit()
    record = db.scalar(
        select(SalaryRecord)
        .options(*_record_options())
        .where(SalaryRecord.id == salary_id)
    )
    assert record is not None
    return _to_read(record)


@manager_router.put("/{salary_id}/issue", response_model=SalaryRead)
def issue_salary_record(
    salary_id: int,
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> SalaryRead:
    """经理发放薪资草稿，发放后员工端才能看到。"""

    record = db.scalar(
        select(SalaryRecord)
        .options(*_record_options())
        .where(SalaryRecord.id == salary_id)
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="薪资记录不存在",
        )
    if record.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该薪资记录已经发放",
        )

    record.status = "issued"
    record.issued_at = datetime.now()
    db.commit()

    record = db.scalar(
        select(SalaryRecord)
        .options(*_record_options())
        .where(SalaryRecord.id == salary_id)
    )
    assert record is not None
    return _to_read(record)
