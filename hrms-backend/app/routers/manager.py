"""经理端员工、考勤、请假和公告管理接口。"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import require_manager
from app.core.security import get_password_hash
from app.database import get_db
from app.models.attendance import Attendance
from app.models.department import Department
from app.models.leave import LeaveRequest
from app.models.notice import Notice
from app.models.position import Position
from app.models.role import Role
from app.models.user import User
from app.schemas.attendance import AttendanceRead, AttendanceStat
from app.schemas.leave import LeaveRead, LeaveReview
from app.schemas.notice import NoticeCreate, NoticeRead, NoticeUpdate
from app.schemas.user import (
    DepartmentRead,
    EmployeeCreate,
    EmployeeUpdate,
    PositionRead,
    RoleRead,
    UserProfileRead,
)


router = APIRouter()


def _attendance_to_read(record: Attendance) -> AttendanceRead:
    """转换考勤记录并附带员工姓名和部门。"""

    return AttendanceRead(
        id=record.id,
        user_id=record.user_id,
        user_name=record.user.name if record.user else None,
        department=record.user.department if record.user else None,
        date=record.date,
        check_in=record.check_in,
        check_out=record.check_out,
        status=record.status,
        remark=record.remark,
        created_at=record.created_at,
    )


def _leave_to_read(record: LeaveRequest) -> LeaveRead:
    """转换请假记录并附带申请人和审批人姓名。"""

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


def _notice_to_read(notice: Notice) -> NoticeRead:
    """转换公告记录并附带发布人姓名。"""

    return NoticeRead(
        id=notice.id,
        title=notice.title,
        content=notice.content,
        author_id=notice.author_id,
        author_name=notice.author.name if notice.author else None,
        created_at=notice.created_at,
    )


def _month_bounds(month: str) -> tuple[date, date]:
    """把 YYYY-MM 转换为该月的起止日期范围。"""

    parsed = datetime.strptime(month, "%Y-%m")
    # 同样使用半开区间，避免计算当月最后一天。
    start = date(parsed.year, parsed.month, 1)
    if parsed.month == 12:
        end = date(parsed.year + 1, 1, 1)
    else:
        end = date(parsed.year, parsed.month + 1, 1)
    return start, end


def _employee_role_id(db: Session) -> int:
    """获取员工角色 ID。"""

    role = db.scalar(select(Role).where(Role.code == "employee"))
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="员工角色未初始化",
        )
    return role.id


def _resolve_department(
    db: Session,
    department_name: str | None,
) -> Department | None:
    """根据部门名称查找或创建部门记录。"""

    if department_name is None or not department_name.strip():
        return None

    name = department_name.strip()
    department = db.scalar(
        select(Department).where(Department.name == name)
    )
    if department is None:
        # 经理在员工表单中直接输入新部门时自动建表记录，
        # 避免必须先进入独立的部门维护页面。
        department = Department(name=name)
        db.add(department)
        # flush 让新部门立即获得 id，但事务尚未最终 commit。
        db.flush()
    return department


def _resolve_position(
    db: Session,
    position_name: str | None,
    department: Department | None,
) -> Position | None:
    """根据职位名称和所属部门查找或创建职位记录。"""

    if position_name is None or not position_name.strip():
        return None
    if department is None:
        # 职位必须挂在部门下，保证 position.department_id 外键有效。
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="填写职位前请先填写部门",
        )

    name = position_name.strip()
    position = db.scalar(
        select(Position).where(
            Position.department_id == department.id,
            Position.name == name,
        )
    )
    if position is None:
        position = Position(
            department_id=department.id,
            name=name,
        )
        db.add(position)
        db.flush()
    return position


def _load_employee_profile(db: Session, employee_id: int) -> User:
    """加载完整的员工资料，避免接口返回时反复查询关联表。"""

    employee = db.scalar(
        select(User)
        .options(
            # 一次性加载角色、部门和职位，避免响应序列化时产生 N+1 查询。
            joinedload(User.role_ref),
            joinedload(User.department_ref),
            joinedload(User.position_ref),
        )
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


@router.get("/references/roles", response_model=list[RoleRead])
def get_roles(
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> list[RoleRead]:
    """经理查看系统角色选项。"""

    roles = db.scalars(select(Role).order_by(Role.id.asc())).all()
    return [RoleRead.model_validate(role) for role in roles]


@router.get("/references/departments", response_model=list[DepartmentRead])
def get_departments(
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> list[DepartmentRead]:
    """经理查看部门选项。"""

    departments = db.scalars(
        select(Department).order_by(Department.name.asc())
    ).all()
    return [
        DepartmentRead.model_validate(department)
        for department in departments
    ]


@router.get("/references/positions", response_model=list[PositionRead])
def get_positions(
    department_id: int | None = Query(default=None),
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> list[PositionRead]:
    """经理查看职位选项，可按部门筛选。"""

    statement = select(Position).order_by(Position.name.asc())
    if department_id is not None:
        statement = statement.where(
            Position.department_id == department_id
        )
    positions = db.scalars(statement).all()
    return [PositionRead.model_validate(position) for position in positions]


@router.get("/employees", response_model=list[UserProfileRead])
def get_employees(
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> list[UserProfileRead]:
    """经理查看全部员工。"""

    employees = db.scalars(
        select(User)
        .options(
            joinedload(User.role_ref),
            joinedload(User.department_ref),
            joinedload(User.position_ref),
        )
        # 员工管理只能看到 employee，不能把经理账号当成员工编辑。
        .where(User.role_ref.has(Role.code == "employee"))
        .order_by(User.id.asc())
    ).all()
    return [UserProfileRead.model_validate(employee) for employee in employees]


@router.post("/employees", response_model=UserProfileRead)
def create_employee(
    payload: EmployeeCreate,
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> UserProfileRead:
    """经理新增员工账号。"""

    # 用户名必须全局唯一，先查一次可以给前端返回明确的中文提示；
    # 数据库唯一索引仍是防止并发重复的最终保障。
    exists = db.scalar(
        select(User).where(User.username == payload.username)
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    department = _resolve_department(db, payload.department)
    position = _resolve_position(db, payload.position, department)
    employee = User(
        username=payload.username,
        # 只保存 bcrypt 哈希，绝不保存明文密码。
        password_hash=get_password_hash(payload.password),
        role_id=_employee_role_id(db),
        name=payload.name,
        gender=payload.gender,
        phone=payload.phone,
        email=payload.email,
        department_id=department.id if department else None,
        position_id=position.id if position else None,
        hire_date=payload.hire_date,
        is_active=payload.is_active,
    )
    db.add(employee)
    db.commit()
    return UserProfileRead.model_validate(_load_employee_profile(db, employee.id))


@router.put("/employees/{employee_id}", response_model=UserProfileRead)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> UserProfileRead:
    """经理编辑员工资料，传入 password 时同时重置密码。"""

    employee = _load_employee_profile(db, employee_id)

    # exclude_unset=True 表示只处理前端真正传过来的字段，
    # 未传字段保持数据库原值，支持局部更新。
    update_data = payload.model_dump(exclude_unset=True)
    if "username" in update_data:
        if update_data["username"] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名不能为空",
            )
        duplicate = db.scalar(
            select(User).where(
                User.username == update_data["username"],
                User.id != employee_id,
            )
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在",
            )

    if "name" in update_data and update_data["name"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="姓名不能为空",
        )
    if "is_active" in update_data and update_data["is_active"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="启用状态不能为空",
        )

    password = update_data.pop("password", None)
    if password is not None:
        # 重置密码与普通资料编辑共用接口，但密码必须先转换为哈希。
        employee.password_hash = get_password_hash(password)

    department = employee.department_ref
    if "department" in update_data:
        department = _resolve_department(
            db,
            update_data.pop("department"),
        )
        employee.department_id = department.id if department else None
        if "position" not in update_data:
            # 部门变化且没有显式传职位时，清空旧职位，避免出现跨部门职位不一致。
            employee.position_id = None

    if "position" in update_data:
        position = _resolve_position(
            db,
            update_data.pop("position"),
            department,
        )
        employee.position_id = position.id if position else None

    for field, value in update_data.items():
        setattr(employee, field, value)

    db.commit()
    return UserProfileRead.model_validate(_load_employee_profile(db, employee.id))


@router.put("/employees/{employee_id}/disable")
def toggle_employee_status(
    employee_id: int,
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """经理禁用或重新启用员工账号。"""

    employee = _load_employee_profile(db, employee_id)

    # 一个接口完成禁用和启用，状态取反后由前端根据返回值提示。
    employee.is_active = not employee.is_active
    db.commit()
    db.refresh(employee)
    return {
        "message": "员工已启用" if employee.is_active else "员工已禁用",
        "id": employee.id,
        "is_active": employee.is_active,
    }


@router.get("/attendance", response_model=list[AttendanceRead])
def get_all_attendance(
    attendance_date: date | None = Query(default=None, alias="date"),
    department: str | None = Query(default=None),
    name: str | None = Query(default=None),
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> list[AttendanceRead]:
    """经理按日期、部门或姓名筛选全部考勤记录。"""

    statement = (
        select(Attendance)
        # join User 用于按姓名、部门筛选；joinedload 用于生成包含用户信息的响应。
        .join(User, Attendance.user_id == User.id)
        .options(
            joinedload(Attendance.user).joinedload(User.department_ref)
        )
        # 考勤管理只统计员工，不包含经理自己的账号。
        .where(User.role_ref.has(Role.code == "employee"))
    )
    if attendance_date is not None:
        statement = statement.where(Attendance.date == attendance_date)
    if department:
        statement = statement.where(
            User.department_ref.has(Department.name == department)
        )
    if name:
        statement = statement.where(User.name.like(f"%{name}%"))

    records = db.scalars(
        statement.order_by(
            Attendance.date.desc(),
            User.name.asc(),
        )
    ).all()
    return [_attendance_to_read(record) for record in records]


@router.get("/attendance/stat", response_model=AttendanceStat)
def get_attendance_stat(
    month: str = Query(
        ...,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="月份，格式 YYYY-MM",
    ),
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> AttendanceStat:
    """经理查看指定月份全部员工的考勤统计。"""

    start, end = _month_bounds(month)
    rows = db.execute(
        # 交给 MySQL 按状态分组统计，避免把所有考勤记录加载到 Python 内存。
        select(Attendance.status, func.count(Attendance.id))
        .where(
            Attendance.date >= start,
            Attendance.date < end,
        )
        .group_by(Attendance.status)
    ).all()
    counts = {record_status: count for record_status, count in rows}

    normal = counts.get("normal", 0)
    late = counts.get("late", 0)
    early = counts.get("early", 0)
    late_early = counts.get("late_early", 0)
    missing = counts.get("missing", 0)
    absent = counts.get("absent", 0)
    total_records = sum(counts.values())
    # 出勤率只把四种“完成上下班”的状态算作已出勤。
    attended = normal + late + early + late_early
    attendance_rate = (
        round(attended / total_records * 100, 2)
        if total_records > 0
        else 0.0
    )

    return AttendanceStat(
        month=month,
        total_records=total_records,
        normal=normal,
        late=late,
        early=early,
        late_early=late_early,
        missing=missing,
        absent=absent,
        attendance_rate=attendance_rate,
    )


@router.get("/leave/pending", response_model=list[LeaveRead])
def get_pending_leaves(
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> list[LeaveRead]:
    """经理查看待审批请假申请。"""

    records = db.scalars(
        select(LeaveRequest)
        .options(
            joinedload(LeaveRequest.user),
            joinedload(LeaveRequest.leave_type),
            joinedload(LeaveRequest.approver),
        )
        # 先提交的申请先显示，符合日常审批顺序。
        .where(LeaveRequest.status == "pending")
        .order_by(LeaveRequest.created_at.asc())
    ).all()
    return [_leave_to_read(record) for record in records]


@router.get("/leave/history", response_model=list[LeaveRead])
def get_leave_history(
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> list[LeaveRead]:
    """经理查看已审批和已撤销的历史记录。"""

    records = db.scalars(
        select(LeaveRequest)
        .options(
            joinedload(LeaveRequest.user),
            joinedload(LeaveRequest.leave_type),
            joinedload(LeaveRequest.approver),
        )
        # 历史包含已通过、已驳回和员工主动撤销的申请。
        .where(
            LeaveRequest.status.in_(["approved", "rejected", "cancelled"])
        )
        .order_by(
            LeaveRequest.approve_time.desc(),
            LeaveRequest.created_at.desc(),
        )
    ).all()
    return [_leave_to_read(record) for record in records]


@router.put("/leave/{leave_id}/approve", response_model=LeaveRead)
def approve_leave(
    leave_id: int,
    payload: LeaveReview,
    current_manager: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> LeaveRead:
    """经理通过请假申请。"""

    record = db.scalar(
        select(LeaveRequest)
        .options(
            joinedload(LeaveRequest.user),
            joinedload(LeaveRequest.leave_type),
            joinedload(LeaveRequest.approver),
        )
        .where(LeaveRequest.id == leave_id)
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="请假申请不存在",
        )
    # 只有 pending 才能审批，防止两个经理重复处理同一条申请。
    if record.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该申请已经处理，不能重复审批",
        )

    record.status = "approved"
    # 记录审批人和审批时间，形成可追溯的历史。
    record.approver_id = current_manager.id
    record.approve_comment = payload.comment
    record.approve_time = datetime.now()
    db.commit()
    db.refresh(record)
    return _leave_to_read(record)


@router.put("/leave/{leave_id}/reject", response_model=LeaveRead)
def reject_leave(
    leave_id: int,
    payload: LeaveReview,
    current_manager: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> LeaveRead:
    """经理驳回请假申请。"""

    record = db.scalar(
        select(LeaveRequest)
        .options(
            joinedload(LeaveRequest.user),
            joinedload(LeaveRequest.leave_type),
            joinedload(LeaveRequest.approver),
        )
        .where(LeaveRequest.id == leave_id)
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="请假申请不存在",
        )
    # 驳回与通过使用相同的状态保护，保证审批结果不可重复覆盖。
    if record.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该申请已经处理，不能重复审批",
        )

    record.status = "rejected"
    record.approver_id = current_manager.id
    record.approve_comment = payload.comment
    record.approve_time = datetime.now()
    db.commit()
    db.refresh(record)
    return _leave_to_read(record)


@router.post("/notice", response_model=NoticeRead)
def create_notice(
    payload: NoticeCreate,
    current_manager: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> NoticeRead:
    """经理发布公告。"""

    notice = Notice(
        title=payload.title,
        content=payload.content,
        # 发布人直接取当前经理，前端不能伪造 author_id。
        author_id=current_manager.id,
    )
    db.add(notice)
    db.commit()
    db.refresh(notice)
    return _notice_to_read(notice)


@router.put("/notice/{notice_id}", response_model=NoticeRead)
def update_notice(
    notice_id: int,
    payload: NoticeUpdate,
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> NoticeRead:
    """经理编辑公告。"""

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

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有需要修改的内容",
        )
    for required_field in ("title", "content"):
        # Pydantic 允许多字段更新，但标题和内容一旦出现就不能为 null。
        if required_field in update_data and update_data[required_field] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="公告标题和内容不能为空",
            )
    for field, value in update_data.items():
        setattr(notice, field, value)

    db.commit()
    db.refresh(notice)
    return _notice_to_read(notice)


@router.delete("/notice/{notice_id}")
def delete_notice(
    notice_id: int,
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """经理删除公告。"""

    notice = db.get(Notice, notice_id)
    if notice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公告不存在",
        )

    db.delete(notice)
    # 物理删除公告；如需保留历史可以改为增加 is_deleted 字段做逻辑删除。
    db.commit()
    return {"message": "公告已删除", "id": notice_id}
