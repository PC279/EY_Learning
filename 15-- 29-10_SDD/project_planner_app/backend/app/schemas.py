from datetime import date
from pydantic import BaseModel, Field, field_validator


class RegisterIn(BaseModel):
    email: str
    full_name: str = Field(default="", max_length=120)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return value


class LoginIn(BaseModel):
    email: str
    password: str


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = Field(default="#64748B", pattern=r"^#[0-9A-Fa-f]{6}$")


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str = ""
    category_id: int | None = None
    priority: str = "medium"
    scheduled_date: date
    recurrence_type: str = "none"  # none/daily/weekly/weekly_count/monthly/custom
    interval_days: int = Field(default=1, ge=1, le=365)
    weekdays: list[int] = Field(default_factory=list)
    weekly_target: int = Field(default=0, ge=0, le=7)
    end_date: date | None = None

    @field_validator("priority")
    @classmethod
    def priority_allowed(cls, value: str) -> str:
        if value not in {"high", "medium", "low"}:
            raise ValueError("Priority must be high, medium or low")
        return value

    @field_validator("recurrence_type")
    @classmethod
    def recurrence_allowed(cls, value: str) -> str:
        if value not in {"none", "daily", "weekly", "weekly_count", "monthly", "custom"}:
            raise ValueError("Unsupported recurrence type")
        return value

    @field_validator("weekdays")
    @classmethod
    def weekdays_allowed(cls, value: list[int]) -> list[int]:
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("Weekdays must be between 0 (Monday) and 6 (Sunday)")
        return sorted(set(value))


class TaskStatusIn(BaseModel):
    completed: bool


class MoveTaskIn(BaseModel):
    destination_date: date


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str = ""
    level: str = "weekly"
    start_date: date
    due_date: date
    parent_goal_id: int | None = None
    tracking_mode: str = "linked"

    @field_validator("level")
    @classmethod
    def level_allowed(cls, value: str) -> str:
        if value not in {"parent", "monthly", "weekly", "custom"}:
            raise ValueError("Unsupported goal level")
        return value


class LinkTaskIn(BaseModel):
    task_id: int


class NoteIn(BaseModel):
    period_type: str
    period_key: str
    body: str = ""


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    timezone: str
    week_start: int

    model_config = {"from_attributes": True}


class TaskEdit(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    priority: str | None = None
    category_id: int | None = None

    @field_validator("priority")
    @classmethod
    def edit_priority_allowed(cls, value: str | None) -> str | None:
        if value is not None and value not in {"high", "medium", "low"}:
            raise ValueError("Priority must be high, medium or low")
        return value
