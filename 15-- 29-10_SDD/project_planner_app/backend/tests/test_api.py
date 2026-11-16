from datetime import date, timedelta


def test_register_creates_general_category_and_me(client):
    response = client.post("/auth/register", json={
        "email": "piyush@example.com", "full_name": "Piyush", "password": "strong-password-123"
    })
    assert response.status_code == 201
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/me", headers=headers).json()["email"] == "piyush@example.com"
    categories = client.get("/categories", headers=headers).json()
    assert len(categories) == 1
    assert categories[0]["name"] == "General"
    assert categories[0]["is_default"] is True


def test_task_category_fallback_and_weekly_goal_progress(client, auth_headers):
    headers = auth_headers
    today = date.today()
    monday = today + timedelta(days=(7 - today.weekday()) % 7)
    if monday <= today:
        monday += timedelta(days=7)
    category = client.post("/categories", headers=headers, json={"name": "Fitness", "color": "#1F9D8B"})
    assert category.status_code == 201
    task = client.post("/tasks", headers=headers, json={
        "title": "Gym session", "category_id": category.json()["id"], "priority": "high",
        "scheduled_date": monday.isoformat(), "recurrence_type": "weekly", "weekdays": [0, 1, 2]
    })
    assert task.status_code == 201, task.text
    occurrences = client.get("/tasks", headers=headers, params={
        "start_date": monday.isoformat(), "end_date": (monday + timedelta(days=6)).isoformat()
    }).json()
    assert len(occurrences) == 3
    goal = client.post("/goals", headers=headers, json={
        "title": "Gym three times", "level": "weekly", "start_date": monday.isoformat(),
        "due_date": (monday + timedelta(days=6)).isoformat(), "tracking_mode": "linked"
    })
    assert goal.status_code == 201
    goal_id = goal.json()["id"]
    for occurrence in occurrences:
        linked = client.post(f"/goals/{goal_id}/tasks", headers=headers, json={"task_id": occurrence["id"]})
        assert linked.status_code == 200
    done = client.patch(f"/tasks/{occurrences[0]['id']}/status", headers=headers, json={"completed": True})
    assert done.status_code == 200
    goals = client.get("/goals", headers=headers).json()
    assert goals[0]["completed"] == 1
    assert goals[0]["total"] == 3
    assert goals[0]["progress"] == 33


def test_past_task_cannot_be_completed_but_can_be_moved_forward(client, auth_headers):
    headers = auth_headers
    yesterday = date.today() - timedelta(days=1)
    created = client.post("/tasks", headers=headers, json={
        "title": "Unfinished task", "scheduled_date": yesterday.isoformat(), "recurrence_type": "none"
    })
    assert created.status_code == 201
    task_id = created.json()["id"]
    blocked = client.patch(f"/tasks/{task_id}/status", headers=headers, json={"completed": True})
    assert blocked.status_code == 403
    moved = client.post(f"/tasks/{task_id}/move", headers=headers, json={"destination_date": date.today().isoformat()})
    assert moved.status_code == 200
    assert moved.json()["scheduled_date"] == date.today().isoformat()
    assert moved.json()["moved_from_id"] == task_id


def test_notes_and_analytics(client, auth_headers):
    headers = auth_headers
    today = date.today()
    note = client.put("/notes", headers=headers, json={
        "period_type": "day", "period_key": today.isoformat(), "body": "Focus on the important work."
    })
    assert note.status_code == 200
    fetched = client.get("/notes", headers=headers, params={"period_type": "day", "period_key": today.isoformat()})
    assert fetched.json()["body"] == "Focus on the important work."
    task = client.post("/tasks", headers=headers, json={"title": "Read", "scheduled_date": today.isoformat()})
    assert task.status_code == 201
    client.patch(f"/tasks/{task.json()['id']}/status", headers=headers, json={"completed": True})
    stats = client.get("/analytics", headers=headers, params={"start_date": today.isoformat(), "end_date": today.isoformat()})
    assert stats.status_code == 200
    assert stats.json()["total_tasks"] == 1
    assert stats.json()["completed_tasks"] == 1
    assert stats.json()["completion_rate"] == 100


def test_habit_analytics_uses_weekly_target(client, auth_headers):
    headers = auth_headers
    today = date.today()
    created = client.post("/tasks", headers=headers, json={
        "title": "Stretch", "scheduled_date": today.isoformat(), "recurrence_type": "weekly_count", "weekly_target": 3
    })
    assert created.status_code == 201
    week = client.get("/tasks", headers=headers, params={
        "start_date": today.isoformat(), "end_date": (today + timedelta(days=6)).isoformat()
    }).json()
    assert len(week) == 7
    for occurrence in week[:2]:
        assert client.patch(f"/tasks/{occurrence['id']}/status", headers=headers, json={"completed": True}).status_code == 200
    stats = client.get("/analytics", headers=headers, params={
        "start_date": today.isoformat(), "end_date": (today + timedelta(days=6)).isoformat()
    }).json()
    assert stats["habits"][0]["completed_occurrences"] == 2
    assert stats["habits"][0]["expected_completions"] == 3
    assert stats["habits"][0]["progress"] == 67


def test_health_checks_database_connection(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"


def test_parent_goal_rolls_up_child_task_completion(client, auth_headers):
    headers = auth_headers
    today = date.today()
    parent = client.post("/goals", headers=headers, json={
        "title": "Build a healthier routine", "level": "parent", "start_date": today.isoformat(),
        "due_date": (today + timedelta(days=30)).isoformat(), "tracking_mode": "linked"
    })
    assert parent.status_code == 201
    child = client.post("/goals", headers=headers, json={
        "title": "Gym this week", "level": "weekly", "start_date": today.isoformat(),
        "due_date": (today + timedelta(days=6)).isoformat(), "parent_goal_id": parent.json()["id"],
        "tracking_mode": "linked"
    })
    assert child.status_code == 201
    task = client.post("/tasks", headers=headers, json={"title": "Gym session", "scheduled_date": today.isoformat()})
    assert task.status_code == 201
    client.post(f"/goals/{child.json()['id']}/tasks", headers=headers, json={"task_id": task.json()["id"]})
    client.patch(f"/tasks/{task.json()['id']}/status", headers=headers, json={"completed": True})
    roots = client.get("/goals", headers=headers).json()
    assert roots[0]["progress"] == 100
    assert roots[0]["achieved"] is True
    assert roots[0]["children"][0]["progress"] == 100
