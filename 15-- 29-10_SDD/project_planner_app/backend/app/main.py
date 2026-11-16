from datetime import date, datetime, timedelta, timezone
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, joinedload

from .config import FRONTEND_ORIGIN
from .database import Base, engine, get_db
from . import models, schemas
from .security import create_access_token, decode_access_token, hash_password, verify_password

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Project Planner API", version="1.0.0", description="API for the Project Planner & Habit Tracker", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    user_id = decode_access_token(token)
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User account not found")
    return user


def require_owned_category(db: Session, user_id: int, category_id: int | None) -> models.Category:
    if category_id is None:
        category = db.scalar(select(models.Category).where(models.Category.user_id == user_id, models.Category.is_default.is_(True)))
    else:
        category = db.scalar(select(models.Category).where(models.Category.id == category_id, models.Category.user_id == user_id, models.Category.archived.is_(False)))
    if not category:
        raise HTTPException(status_code=400, detail="Category not found for this user")
    return category


def task_payload(occ: models.TaskOccurrence) -> dict:
    series = occ.series
    return {
        "id": occ.id,
        "series_id": series.id,
        "title": series.title,
        "description": series.description,
        "priority": series.priority,
        "category_id": series.category_id,
        "category_name": series.category.name,
        "category_color": series.category.color,
        "scheduled_date": occ.scheduled_date.isoformat(),
        "status": occ.status,
        "completed": occ.status == "completed",
        "completed_at": occ.completed_at.isoformat() if occ.completed_at else None,
        "recurrence_type": series.recurrence_type,
        "weekly_target": series.weekly_target,
        "weekdays": [int(x) for x in series.weekdays.split(",") if x != ""],
        "moved_from_id": occ.moved_from_id,
    }


def goal_tree_progress(db: Session, goal: models.Goal, seen: set[int] | None = None) -> dict:
    seen = seen or set()
    if goal.id in seen:
        return {"id": goal.id, "title": goal.title, "progress": 0, "completed": 0, "total": 0, "achieved": False}
    seen.add(goal.id)
    db.refresh(goal)
    child_progress = [goal_tree_progress(db, child, seen.copy()) for child in goal.children]
    direct_tasks = list(goal.tasks)
    completed = sum(1 for task in direct_tasks if task.status == "completed")
    total = len(direct_tasks)
    completed += sum(x["completed"] for x in child_progress)
    total += sum(x["total"] for x in child_progress)
    if goal.tracking_mode == "manual":
        completed = 1 if goal.manual_completed else 0
        total = 1
        progress = 100 if goal.manual_completed else 0
        achieved = bool(goal.manual_completed)
    else:
        progress = round((completed / total) * 100) if total else 0
        achieved = total > 0 and completed == total
    return {
        "id": goal.id,
        "title": goal.title,
        "description": goal.description,
        "level": goal.level,
        "start_date": goal.start_date.isoformat(),
        "due_date": goal.due_date.isoformat(),
        "parent_goal_id": goal.parent_goal_id,
        "progress": progress,
        "completed": completed,
        "total": total,
        "achieved": achieved,
        "children": child_progress,
        "linked_task_ids": [task.id for task in direct_tasks],
    }


def create_occurrences(db: Session, series: models.TaskSeries) -> None:
    start = series.start_date
    stop = min(series.end_date or (start + timedelta(days=365)), start + timedelta(days=365))
    weekdays = {int(x) for x in series.weekdays.split(",") if x != ""}
    dates: list[date] = []
    cursor = start
    while cursor <= stop:
        offset = (cursor - start).days
        include = False
        if series.recurrence_type == "none":
            include = cursor == start
        elif series.recurrence_type == "daily":
            include = True
        elif series.recurrence_type == "weekly":
            include = cursor.weekday() in (weekdays or {start.weekday()})
        elif series.recurrence_type == "weekly_count":
            # Without specified weekdays, the task is available daily; weekly_target
            # tells the tracker how many completions count as the weekly target.
            include = cursor.weekday() in (weekdays or set(range(7)))
        elif series.recurrence_type == "monthly":
            include = cursor.day == start.day
        elif series.recurrence_type == "custom":
            include = offset % series.interval_days == 0
        if include:
            dates.append(cursor)
        cursor += timedelta(days=1)
    db.add_all([models.TaskOccurrence(series=series, scheduled_date=day, status="open") for day in dates])


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected", "service": "project-planner-api"}


@app.post("/auth/register", status_code=201)
def register(payload: schemas.RegisterIn, db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(models.User).where(models.User.email == payload.email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = models.User(email=payload.email, full_name=payload.full_name, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    db.add(models.Category(user_id=user.id, name="General", color="#64748B", is_default=True))
    db.commit()
    db.refresh(user)
    return {"access_token": create_access_token(user.id), "token_type": "bearer", "user": schemas.UserOut.model_validate(user).model_dump()}


@app.post("/auth/login")
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(models.User).where(models.User.email == payload.email.strip().lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"access_token": create_access_token(user.id), "token_type": "bearer", "user": schemas.UserOut.model_validate(user).model_dump()}


@app.get("/auth/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(current_user)) -> models.User:
    return user


@app.get("/categories")
def list_categories(db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> list[dict]:
    rows = db.scalars(select(models.Category).where(models.Category.user_id == user.id, models.Category.archived.is_(False)).order_by(models.Category.is_default.desc(), models.Category.name)).all()
    return [{"id": x.id, "name": x.name, "color": x.color, "is_default": x.is_default} for x in rows]


@app.post("/categories", status_code=201)
def add_category(payload: schemas.CategoryIn, db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> dict:
    name = payload.name.strip()
    if db.scalar(select(models.Category).where(models.Category.user_id == user.id, func.lower(models.Category.name) == name.lower())):
        raise HTTPException(status_code=409, detail="A category with this name already exists")
    item = models.Category(user_id=user.id, name=name, color=payload.color.upper())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "name": item.name, "color": item.color, "is_default": item.is_default}


@app.delete("/categories/{category_id}")
def archive_category(category_id: int, db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> dict:
    category = db.scalar(select(models.Category).where(models.Category.id == category_id, models.Category.user_id == user.id))
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if category.is_default:
        raise HTTPException(status_code=400, detail="The General category cannot be deleted")
    general = require_owned_category(db, user.id, None)
    series = db.scalars(select(models.TaskSeries).where(models.TaskSeries.category_id == category.id, models.TaskSeries.user_id == user.id)).all()
    for item in series:
        item.category_id = general.id
    category.archived = True
    db.commit()
    return {"message": "Category archived; its tasks were moved to General"}


@app.post("/tasks", status_code=201)
def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> dict:
    if payload.end_date and payload.end_date < payload.scheduled_date:
        raise HTTPException(status_code=400, detail="End date cannot be earlier than the start date")
    category = require_owned_category(db, user.id, payload.category_id)
    if payload.recurrence_type == "weekly" and not payload.weekdays:
        raise HTTPException(status_code=400, detail="Choose at least one weekday for a weekly task")
    series = models.TaskSeries(
        user_id=user.id, title=payload.title.strip(), description=payload.description,
        category_id=category.id, priority=payload.priority, recurrence_type=payload.recurrence_type,
        interval_days=payload.interval_days, weekdays=",".join(str(x) for x in payload.weekdays),
        weekly_target=payload.weekly_target, start_date=payload.scheduled_date, end_date=payload.end_date,
    )
    db.add(series)
    db.flush()
    create_occurrences(db, series)
    db.commit()
    first = db.scalar(select(models.TaskOccurrence).where(models.TaskOccurrence.series_id == series.id).order_by(models.TaskOccurrence.scheduled_date).limit(1))
    return task_payload(first)


@app.get("/tasks")
def list_tasks(start_date: date, end_date: date, db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> list[dict]:
    if end_date < start_date or (end_date - start_date).days > 400:
        raise HTTPException(status_code=400, detail="Choose a valid date range of 400 days or fewer")
    rows = db.scalars(
        select(models.TaskOccurrence).join(models.TaskSeries).options(joinedload(models.TaskOccurrence.series).joinedload(models.TaskSeries.category))
        .where(models.TaskSeries.user_id == user.id, models.TaskOccurrence.scheduled_date.between(start_date, end_date), models.TaskOccurrence.status.notin_(["moved", "cancelled"]))
        .order_by(models.TaskOccurrence.scheduled_date, models.TaskSeries.priority, models.TaskSeries.title)
    ).unique().all()
    return [task_payload(x) for x in rows]


@app.patch("/tasks/{task_id}/status")
def set_task_status(task_id: int, payload: schemas.TaskStatusIn, db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> dict:
    task = db.scalar(select(models.TaskOccurrence).join(models.TaskSeries).options(joinedload(models.TaskOccurrence.series).joinedload(models.TaskSeries.category)).where(models.TaskOccurrence.id == task_id, models.TaskSeries.user_id == user.id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.scheduled_date < date.today():
        raise HTTPException(status_code=403, detail="Past tasks are read-only. Move the task forward to complete it.")
    task.status = "completed" if payload.completed else "open"
    task.completed_at = datetime.now(timezone.utc) if payload.completed else None
    db.commit()
    db.refresh(task)
    return task_payload(task)


@app.patch("/tasks/{task_id}")
def edit_task(task_id: int, payload: schemas.TaskEdit, db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> dict:
    task = db.scalar(select(models.TaskOccurrence).join(models.TaskSeries).options(joinedload(models.TaskOccurrence.series).joinedload(models.TaskSeries.category)).where(models.TaskOccurrence.id == task_id, models.TaskSeries.user_id == user.id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.scheduled_date < date.today():
        raise HTTPException(status_code=403, detail="Past tasks are read-only")
    fields = payload.model_fields_set
    if "title" in fields and payload.title is not None:
        task.series.title = payload.title.strip()
    if "description" in fields and payload.description is not None:
        task.series.description = payload.description
    if "priority" in fields and payload.priority is not None:
        task.series.priority = payload.priority
    if "category_id" in fields:
        category = require_owned_category(db, user.id, payload.category_id)
        task.series.category_id = category.id
    db.commit()
    db.refresh(task)
    return task_payload(task)


@app.post("/tasks/{task_id}/move")
def move_task(task_id: int, payload: schemas.MoveTaskIn, db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> dict:
    task = db.scalar(select(models.TaskOccurrence).join(models.TaskSeries).options(joinedload(models.TaskOccurrence.series).joinedload(models.TaskSeries.category)).where(models.TaskOccurrence.id == task_id, models.TaskSeries.user_id == user.id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status == "completed":
        raise HTTPException(status_code=400, detail="Completed tasks cannot be moved")
    if payload.destination_date < date.today():
        raise HTTPException(status_code=400, detail="Tasks can only be moved to today or a future date")
    if payload.destination_date == task.scheduled_date:
        return task_payload(task)
    duplicate = db.scalar(select(models.TaskOccurrence).where(
        models.TaskOccurrence.series_id == task.series_id,
        models.TaskOccurrence.scheduled_date == payload.destination_date,
        models.TaskOccurrence.status.in_(["open", "completed"]),
    ))
    if duplicate:
        raise HTTPException(status_code=409, detail="This task already has an occurrence on the selected date")
    original_id = task.id
    task.status = "moved"
    new_task = models.TaskOccurrence(series_id=task.series_id, scheduled_date=payload.destination_date, status="open", moved_from_id=original_id)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return task_payload(new_task)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> dict:
    task = db.scalar(select(models.TaskOccurrence).join(models.TaskSeries).where(models.TaskOccurrence.id == task_id, models.TaskSeries.user_id == user.id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.scheduled_date < date.today():
        raise HTTPException(status_code=403, detail="Past tasks are read-only")
    task.status = "cancelled"
    db.commit()
    return {"message": "Task occurrence cancelled"}


@app.get("/goals")
def list_goals(db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> list[dict]:
    rows = db.scalars(select(models.Goal).where(models.Goal.user_id == user.id, models.Goal.parent_goal_id.is_(None)).order_by(models.Goal.due_date)).all()
    return [goal_tree_progress(db, x) for x in rows]


@app.post("/goals", status_code=201)
def create_goal(payload: schemas.GoalCreate, db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> dict:
    if payload.due_date < payload.start_date:
        raise HTTPException(status_code=400, detail="Goal due date cannot be before its start date")
    if payload.tracking_mode not in {"linked", "manual"}:
        raise HTTPException(status_code=400, detail="Tracking mode must be linked or manual")
    if payload.parent_goal_id:
        parent = db.scalar(select(models.Goal).where(models.Goal.id == payload.parent_goal_id, models.Goal.user_id == user.id))
        if not parent:
            raise HTTPException(status_code=400, detail="Parent goal not found")
    goal = models.Goal(user_id=user.id, title=payload.title.strip(), description=payload.description, level=payload.level,
                       start_date=payload.start_date, due_date=payload.due_date, parent_goal_id=payload.parent_goal_id,
                       tracking_mode=payload.tracking_mode)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal_tree_progress(db, goal)


@app.post("/goals/{goal_id}/tasks")
def link_task(goal_id: int, payload: schemas.LinkTaskIn, db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> dict:
    goal = db.scalar(select(models.Goal).where(models.Goal.id == goal_id, models.Goal.user_id == user.id))
    task = db.scalar(select(models.TaskOccurrence).join(models.TaskSeries).where(models.TaskOccurrence.id == payload.task_id, models.TaskSeries.user_id == user.id))
    if not goal or not task:
        raise HTTPException(status_code=404, detail="Goal or task not found")
    if task not in goal.tasks:
        goal.tasks.append(task)
    db.commit()
    return goal_tree_progress(db, goal)


@app.delete("/goals/{goal_id}/tasks/{task_id}")
def unlink_task(goal_id: int, task_id: int, db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> dict:
    goal = db.scalar(select(models.Goal).where(models.Goal.id == goal_id, models.Goal.user_id == user.id))
    task = db.scalar(select(models.TaskOccurrence).join(models.TaskSeries).where(models.TaskOccurrence.id == task_id, models.TaskSeries.user_id == user.id))
    if not goal or not task:
        raise HTTPException(status_code=404, detail="Goal or task not found")
    if task in goal.tasks:
        goal.tasks.remove(task)
    db.commit()
    return goal_tree_progress(db, goal)


@app.patch("/goals/{goal_id}/manual-status")
def set_manual_goal(goal_id: int, completed: bool, db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> dict:
    goal = db.scalar(select(models.Goal).where(models.Goal.id == goal_id, models.Goal.user_id == user.id))
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal.tracking_mode != "manual":
        raise HTTPException(status_code=400, detail="Only manual goals can be marked manually")
    goal.manual_completed = completed
    db.commit()
    return goal_tree_progress(db, goal)


@app.get("/notes")
def get_note(period_type: str, period_key: str, db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> dict:
    if period_type not in {"day", "week", "month"}:
        raise HTTPException(status_code=400, detail="period_type must be day, week or month")
    note = db.scalar(select(models.Note).where(models.Note.user_id == user.id, models.Note.period_type == period_type, models.Note.period_key == period_key))
    return {"body": note.body if note else ""}


@app.put("/notes")
def save_note(payload: schemas.NoteIn, db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> dict:
    if payload.period_type not in {"day", "week", "month"}:
        raise HTTPException(status_code=400, detail="period_type must be day, week or month")
    if len(payload.period_key) > 20:
        raise HTTPException(status_code=400, detail="Invalid period key")
    note = db.scalar(select(models.Note).where(models.Note.user_id == user.id, models.Note.period_type == payload.period_type, models.Note.period_key == payload.period_key))
    if note:
        note.body = payload.body
    else:
        note = models.Note(user_id=user.id, period_type=payload.period_type, period_key=payload.period_key, body=payload.body)
        db.add(note)
    db.commit()
    return {"body": note.body, "updated_at": note.updated_at.isoformat() if note.updated_at else None}


@app.get("/analytics")
def analytics(start_date: date, end_date: date, db: Session = Depends(get_db), user: models.User = Depends(current_user)) -> dict:
    if end_date < start_date or (end_date - start_date).days > 400:
        raise HTTPException(status_code=400, detail="Choose a valid date range of 400 days or fewer")
    rows = db.scalars(select(models.TaskOccurrence).join(models.TaskSeries).options(joinedload(models.TaskOccurrence.series).joinedload(models.TaskSeries.category)).where(
        models.TaskSeries.user_id == user.id,
        models.TaskOccurrence.scheduled_date.between(start_date, end_date),
        models.TaskOccurrence.status.notin_(["moved", "cancelled"])
    )).unique().all()
    total = len(rows)
    completed = sum(1 for x in rows if x.status == "completed")
    overdue = sum(1 for x in rows if x.status == "open" and x.scheduled_date < date.today())
    by_day: dict[str, dict] = {}
    by_category: dict[str, int] = {}
    for x in rows:
        day_key = x.scheduled_date.isoformat()
        by_day.setdefault(day_key, {"date": day_key, "total": 0, "completed": 0})
        by_day[day_key]["total"] += 1
        if x.status == "completed":
            by_day[day_key]["completed"] += 1
            by_category[x.series.category.name] = by_category.get(x.series.category.name, 0) + 1
    roots = db.scalars(select(models.Goal).where(models.Goal.user_id == user.id, models.Goal.parent_goal_id.is_(None))).all()
    goal_data = [goal_tree_progress(db, x) for x in roots]
    achieved_goals = sum(1 for x in goal_data if x["achieved"])
    habit_groups: dict[int, dict] = {}
    for occurrence in rows:
        series = occurrence.series
        if series.recurrence_type == "none":
            continue
        item = habit_groups.setdefault(series.id, {
            "series_id": series.id, "title": series.title, "category": series.category.name,
            "recurrence_type": series.recurrence_type, "weekly_target": series.weekly_target,
            "scheduled_occurrences": 0, "completed_occurrences": 0,
        })
        item["scheduled_occurrences"] += 1
        if occurrence.status == "completed":
            item["completed_occurrences"] += 1
    habits = []
    for item in habit_groups.values():
        expected = item["scheduled_occurrences"]
        if item["recurrence_type"] == "weekly_count" and item["weekly_target"]:
            weeks = max(1, ((end_date - start_date).days + 1 + 6) // 7)
            expected = min(item["scheduled_occurrences"], weeks * item["weekly_target"])
        item["expected_completions"] = expected
        item["progress"] = min(100, round(item["completed_occurrences"] / expected * 100)) if expected else 0
        habits.append(item)
    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "completion_rate": round(completed / total * 100) if total else 0,
        "overdue_tasks": overdue,
        "goals_achieved": achieved_goals,
        "by_day": sorted(by_day.values(), key=lambda x: x["date"]),
        "completed_by_category": [{"category": key, "completed": value} for key, value in by_category.items()],
        "habits": habits,
    }
