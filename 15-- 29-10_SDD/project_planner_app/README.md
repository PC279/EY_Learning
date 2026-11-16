# Daymark — Project Planner & Habit Tracker

A local full-stack starter implementation based on the Project Planner & Habit Tracker SDD.

## Three connected parts

| Layer | Technology | Folder | Responsibility |
|---|---|---|---|
| Frontend | React 19 + TypeScript + Vite 8 | `frontend/` | UI, calendar views, forms, charts and drag/drop interactions |
| Backend | Python 3.14 + FastAPI + SQLAlchemy | `backend/` | Authentication, validation, recurring tasks, goal progress, notes and analytics |
| Database | PostgreSQL 16 | Your local PostgreSQL server | Durable storage for accounts and planner data |

The frontend calls the backend over HTTP (`http://127.0.0.1:8000`). The backend connects to PostgreSQL using `DATABASE_URL`. The frontend never connects directly to PostgreSQL.

## Requirements

- Windows 10
- Python 3.14.x
- Node.js 22.12 or newer (your Node 22.23.3 is suitable for Vite 8)
- npm
- PostgreSQL 16 and pgAdmin 4
- PyCharm 2026.2.3

## 1. Create the PostgreSQL database in pgAdmin

1. Open **pgAdmin 4** and connect to your local PostgreSQL 16 server.
2. Expand **Servers → PostgreSQL 16 → Databases**.
3. Right-click **Databases → Create → Database…**.
4. Set the database name to `project_planner` and the owner to `postgres`.
5. Click **Save**.

The database must exist before the API starts. The API creates the application tables automatically on startup; you do not need to run table-creation scripts manually.

The optional SQL file at `database/create_database.sql` contains the one-time `CREATE DATABASE` statement. Do not run it again if you already created the database in pgAdmin.

## 2. Configure the backend in PyCharm

1. Extract this project folder somewhere convenient, for example `C:\Users\<you>\PycharmProjects\project_planner_app`.
2. Open the **project_planner_app** root folder in PyCharm.
3. Open **Settings → Project → Python Interpreter** and add a new virtual environment using Python 3.14.7. A virtual environment inside `backend\.venv` is recommended.
4. Open PyCharm's Terminal and run:

```powershell
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks virtual-environment activation, run this for the current terminal only, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

5. Open `backend\.env` in PyCharm and replace `YOUR_POSTGRES_PASSWORD` with the password for the `postgres` database user. Keep the database name, host and port as shown:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/project_planner
JWT_SECRET=replace-this-with-a-long-random-secret-before-real-use
ACCESS_TOKEN_HOURS=24
FRONTEND_ORIGIN=http://localhost:5173
```

If your PostgreSQL password contains URL-reserved characters, URL-encode them in the connection string. For example, `@` becomes `%40`, `#` becomes `%23`, and `%` becomes `%25`. Do not share your `.env` file or commit it to Git.

6. Start the API:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Keep this terminal running. On the first start, SQLAlchemy creates the application tables in `project_planner`.

### Verify the backend and database connection

Open these addresses in a browser:

- `http://127.0.0.1:8000/health` — should return `{"status":"ok","database":"connected",...}`.
- `http://127.0.0.1:8000/docs` — interactive API documentation (Swagger UI).

The health endpoint runs a database query, so `database: connected` confirms that the API reached its configured database. If it fails, check that PostgreSQL is running, that the database exists, and that the password in `.env` is correct.

In pgAdmin, refresh **project_planner → Schemas → public → Tables**. You should see tables including `users`, `categories`, `task_series`, `task_occurrences`, `goals`, `goal_task_links` and `notes`.

## 3. Configure and run the frontend

Open a **second** PyCharm Terminal window (leave the backend running in the first one):

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173` in Chrome or Edge. Register an account; the app creates a `General` category automatically.

If the API is running at a different address, create `frontend\.env` with:

```dotenv
VITE_API_URL=http://127.0.0.1:8000
```

Restart the Vite server after changing frontend environment variables.

## 4. How the connection works

```text
Browser (React / Vite :5173)
        |
        | HTTP requests + bearer access token
        v
Python API (FastAPI :8000)
        |
        | SQLAlchemy + psycopg 3
        v
PostgreSQL 16 (localhost:5432)
        |
        v
project_planner database
```

- The browser stores the access token in local storage and sends it in the `Authorization: Bearer ...` header.
- FastAPI validates the token and applies user ownership checks to each private endpoint.
- SQLAlchemy reads and writes the user's PostgreSQL records.
- The frontend calls the API; it does not contain PostgreSQL credentials.

## 5. Test the application

### Automated backend tests

From the `backend` folder, with the virtual environment active:

```powershell
python -m pytest -q
```

The tests deliberately use a temporary in-memory SQLite database so that test records never pollute your real PostgreSQL database. They cover:

- Registration, login token and automatic `General` category creation.
- Category creation and task creation.
- Weekly recurrence generation and linked goal progress.
- Blocking completion of past tasks and moving unfinished tasks forward.
- Notes saving/retrieval and task analytics.
- Habit completion against a weekly target.
- Database health endpoint behaviour.

### Manual end-to-end test (use the running PostgreSQL app)

1. Register a new account in the browser.
2. Create categories such as `Work`, `Health` and `Personal` with different colours.
3. Add one task for today with High priority, and another for a future date.
4. Tick today's task. Confirm the completion count and progress view update.
5. Add a recurring task. Try daily, selected weekdays, and a weekly target (for example, 3 times per week).
6. Create a weekly goal called `Go to the gym three times` and link three dated gym tasks to it. Complete the task occurrences one by one; check that goal progress changes from `0/3` to `1/3`, `2/3` and `3/3`.
7. Create a parent goal, then create a child goal using the Parent goal selector. Link tasks to the child and check the roll-up progress.
8. Open Month and Week. Drag a task onto another future date. Verify that it appears on the destination date.
9. Create an incomplete task dated yesterday through the API/Swagger UI. In Today, verify it appears under Carry Forward. Try completing it from the past date (the API should reject it), then move it to today and complete the new occurrence.
10. Add daily, weekly and monthly notes. Navigate away and back to verify they persist.
11. In Progress, verify completion rate, category breakdown and habit progress.
12. In pgAdmin, inspect the corresponding records in `task_series`, `task_occurrences`, `goals`, `goal_task_links` and `notes`.

## 6. Useful API endpoints

| Endpoint | Purpose |
|---|---|
| `POST /auth/register` | Create account and seed `General` category |
| `POST /auth/login` | Sign in and return access token |
| `GET /auth/me` | Current user profile |
| `GET/POST /categories` | List and create categories |
| `POST /tasks` | Create one-off or recurring task series |
| `GET /tasks?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` | List scheduled occurrences in a date range |
| `PATCH /tasks/{id}` | Edit title, priority, description or category for its series |
| `PATCH /tasks/{id}/status` | Complete/reopen an occurrence (past dates are blocked) |
| `POST /tasks/{id}/move` | Carry an unfinished occurrence to a future date |
| `GET/POST /goals` | List and create hierarchical goals |
| `POST /goals/{id}/tasks` | Link a task occurrence to a goal |
| `GET/PUT /notes` | Read and save day/week/month notes |
| `GET /analytics` | Completion, category, habit and goal metrics |
| `GET /health` | API and database connectivity check |

## 7. Current implementation notes

This is a runnable MVP foundation, not a production-hardened release. It implements the core daily/weekly/monthly workspace, task categories and colours, priorities, recurring schedules, checkbox completion, task editing, task carry-forward, goal hierarchy and linked-task progress, notes, basic analytics and habit tracking.

Known scope boundaries for this first build:

- Recurring series are pre-generated for up to one year from their start date. Edit currently updates the series definition for all its occurrences; an occurrence-only / future-only edit choice is a follow-up enhancement.
- Weekly-count recurrence creates daily checkable occurrences and calculates the target against the weekly count. A more advanced habit scheduler could allow any-day check-ins without showing a checkbox for every weekday.
- The current goal UI supports parent-child goals and linking existing task occurrences, but does not yet provide a dedicated drag-and-drop goal hierarchy editor.
- Notes save on blur or when the Save notes action is clicked.
- The UI uses responsive CSS charts; there is no external charting service.
- Database schema creation uses SQLAlchemy `create_all` for local development. Before production deployment, add Alembic migrations, HTTPS, secure cookie/token storage, rate limiting, account recovery, backups and stronger operational logging.

## Troubleshooting

**`password authentication failed for user "postgres"`**: Re-check the password in `backend\.env` and make sure the connection URL is correctly URL-encoded.

**`database "project_planner" does not exist`**: Create it in pgAdmin before starting FastAPI.

**`connection refused` on port 5432**: Start the PostgreSQL 16 Windows service and verify the server listens on port 5432.

**Frontend shows `Failed to fetch`**: Confirm the backend terminal is running, visit `/health`, and check the API URL and CORS origin.

**`npm install` fails**: Check internet access and run `npm cache verify`, then retry `npm install` from `frontend`.

**PowerShell cannot activate `.venv`**: Use the process-scoped execution policy command in the backend setup section.
