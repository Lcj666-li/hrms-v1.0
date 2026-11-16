"""考勤相关 Pydantic 模型。"""

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict


class AttendanceRead(BaseModel):
    """单条考勤记录响应。

    user_name 和 department 不是数据库字段，而是由关联的 User 对象拼装，
    这样经理端列表可以直接显示姓名和部门，不需要再发额外的查询请求。
    """

    id: int
    user_id: int
    user_name: str | None = None
    department: str | None = None
    date: date
    check_in: time | None = None
    check_out: time | None = None
    status: str
    remark: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceCheckResponse(BaseModel):
    """打卡成功响应：包含提示语和打卡后的最新记录，前端可直接刷新页面数据。"""

    message: str
    data: AttendanceRead


class AttendanceStat(BaseModel):
    """月度考勤统计。"""

    month: str
    total_records: int
    normal: int
    late: int
    early: int
    late_early: int
    missing: int
    absent: int
    attendance_rate: float
