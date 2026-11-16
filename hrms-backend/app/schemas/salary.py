"""薪资记录相关 Pydantic 模型。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


SALARY_MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


def _validate_salary_month(value: str | None) -> str | None:
    """校验薪资月份格式，并拒绝不存在的月份。"""

    if value is None:
        return None
    try:
        year_text, month_text = value.split("-")
        year = int(year_text)
        month = int(month_text)
    except (AttributeError, TypeError, ValueError):
        raise ValueError("薪资月份格式必须为 YYYY-MM")
    if year < 2000 or year > 2100 or not 1 <= month <= 12:
        raise ValueError("薪资月份超出有效范围")
    return value


class SalaryCreate(BaseModel):
    """经理创建薪资草稿。"""

    user_id: int = Field(gt=0)
    salary_month: str = Field(pattern=SALARY_MONTH_PATTERN)
    base_salary: Decimal = Field(
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    attendance_deduction: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    leave_deduction: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    bonus: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    social_security: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    tax: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=10,
        decimal_places=2,
    )

    @field_validator("salary_month")
    @classmethod
    def validate_salary_month(cls, value: str) -> str:
        validated = _validate_salary_month(value)
        assert validated is not None
        return validated


class SalaryUpdate(BaseModel):
    """经理编辑尚未发放的薪资草稿。"""

    user_id: int | None = Field(default=None, gt=0)
    salary_month: str | None = Field(
        default=None,
        pattern=SALARY_MONTH_PATTERN,
    )
    base_salary: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    attendance_deduction: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    leave_deduction: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    bonus: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    social_security: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    tax: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )

    @field_validator("salary_month")
    @classmethod
    def validate_salary_month(cls, value: str | None) -> str | None:
        return _validate_salary_month(value)


class SalaryRead(BaseModel):
    """薪资记录响应。"""

    id: int
    user_id: int
    user_name: str | None = None
    department: str | None = None
    salary_month: str
    base_salary: Decimal
    attendance_deduction: Decimal
    leave_deduction: Decimal
    bonus: Decimal
    social_security: Decimal
    tax: Decimal
    actual_salary: Decimal
    status: str
    created_by: int
    created_by_name: str | None = None
    issued_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
