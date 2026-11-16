from datetime import date, datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Time, UniqueConstraint, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


goal_task_links = Table(
    "goal_task_links",
    Base.metadata,
    Column("goal_id", ForeignKey("goals.id", ondelete="CASCADE"), primary_key=True),
    Column("task_id", ForeignKey("task_occurrences.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    week_start: Mapped[int] = mapped_column(Integer, default=0)  # Monday
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    categories: Mapped[list["Category"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    task_series: Mapped[list["TaskSeries"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    goals: Mapped[list["Goal"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    color: Mapped[str] = mapped_column(String(7), default="#64748B")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped[User] = relationship(back_populates="categories")
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_category_user_name"),)


class TaskSeries(Base):
    __tablename__ = "task_series"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    recurrence_type: Mapped[str] = mapped_column(String(20), default="none")
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    weekdays: Mapped[str] = mapped_column(String(30), default="")  # comma-separated 0=Mon..6=Sun
    weekly_target: Mapped[int] = mapped_column(Integer, default=0)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user: Mapped[User] = relationship(back_populates="task_series")
    occurrences: Mapped[list["TaskOccurrence"]] = relationship(back_populates="series", cascade="all, delete-orphan")
    category: Mapped[Category] = relationship()


class TaskOccurrence(Base):
    __tablename__ = "task_occurrences"
    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("task_series.id", ondelete="CASCADE"), index=True)
    scheduled_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(12), default="open")  # open/completed/moved/cancelled
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    moved_from_id: Mapped[int | None] = mapped_column(ForeignKey("task_occurrences.id"), nullable=True)
    series: Mapped[TaskSeries] = relationship(back_populates="occurrences", foreign_keys=[series_id])
    goals: Mapped[list["Goal"]] = relationship(secondary=goal_task_links, back_populates="tasks")
    moved_from: Mapped["TaskOccurrence | None"] = relationship(remote_side=[id], foreign_keys=[moved_from_id])


class Goal(Base):
    __tablename__ = "goals"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    parent_goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    level: Mapped[str] = mapped_column(String(20), default="weekly")
    start_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    tracking_mode: Mapped[str] = mapped_column(String(12), default="linked")  # linked/manual
    manual_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped[User] = relationship(back_populates="goals")
    parent: Mapped["Goal | None"] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list["Goal"]] = relationship(back_populates="parent", cascade="all, delete-orphan")
    tasks: Mapped[list[TaskOccurrence]] = relationship(secondary=goal_task_links, back_populates="goals")


class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    period_type: Mapped[str] = mapped_column(String(10))
    period_key: Mapped[str] = mapped_column(String(20))
    body: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint("user_id", "period_type", "period_key", name="uq_note_period"),)
