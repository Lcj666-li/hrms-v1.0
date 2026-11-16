"""请假类型相关 Pydantic 模型。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class LeaveTypeBase(BaseModel):
    """请假类型可维护字段。"""

    code: str = Field(
        min_length=2,
        max_length=30,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    name: str = Field(min_length=1, max_length=50)
    is_paid: bool = True
    max_days_per_year: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=5,
        decimal_places=1,
    )
    requires_approval: bool = True
    is_active: bool = True


class LeaveTypeCreate(LeaveTypeBase):
    """经理新增请假类型。"""


class LeaveTypeUpdate(BaseModel):
    """经理编辑请假类型。"""

    code: str | None = Field(
        default=None,
        min_length=2,
        max_length=30,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    name: str | None = Field(default=None, min_length=1, max_length=50)
    is_paid: bool | None = None
    max_days_per_year: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=5,
        decimal_places=1,
    )
    requires_approval: bool | None = None
    is_active: bool | None = None


class LeaveTypeRead(BaseModel):
    """请假类型响应。"""

    id: int
    code: str
    name: str
    is_paid: bool
    max_days_per_year: Decimal | None = None
    requires_approval: bool
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
