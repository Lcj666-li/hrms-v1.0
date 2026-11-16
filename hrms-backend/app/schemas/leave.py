"""请假相关 Pydantic 模型。"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LeaveCreate(BaseModel):
    """员工提交请假申请。"""

    leave_type_id: int
    start_date: date
    end_date: date
    reason: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_date_range(self) -> "LeaveCreate":
        # 在模型层校验日期区间，保证业务代码里拿到的数据一定合法；
        # 数据库的 CheckConstraint 是第二道防线。
        if self.end_date < self.start_date:
            raise ValueError("结束日期不能早于开始日期")
        return self


class LeaveReview(BaseModel):
    """经理审批请假申请：意见可以为空，通过和驳回共用这个模型。"""

    comment: str | None = Field(default=None, max_length=1000)


class LeaveRead(BaseModel):
    """请假记录响应。"""

    id: int
    user_id: int
    user_name: str | None = None
    department: str | None = None
    leave_type_id: int
    leave_type_name: str | None = None
    leave_type_is_paid: bool | None = None
    start_date: date
    end_date: date
    reason: str
    status: str
    approver_id: int | None = None
    approver_name: str | None = None
    approve_comment: str | None = None
    approve_time: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeaveCancelResponse(BaseModel):
    """撤销请假申请响应。"""

    message: str
    id: int
