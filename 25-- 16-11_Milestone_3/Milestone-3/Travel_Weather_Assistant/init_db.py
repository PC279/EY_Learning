"""Reset trips.db and load a few sample trips. Dates are relative to today so they stay demo-ready.

Run once before the demo:  python init_db.py
"""
from contextlib import closing
from datetime import date, timedelta

import db

# (employee, destination, days from today to start, trip length in days, purpose)
SAMPLE_TRIPS = [
    ("EMP201", "Mumbai", 2, 3, "Quarterly business review"),
    ("EMP202", "Bengaluru", 5, 2, "Product workshop"),
    ("EMP104", "London", 40, 4, "Audit planning"),  # beyond the 16-day forecast window: the failure demo
]

with closing(db._connect()) as conn:
    conn.execute("DROP TABLE IF EXISTS trips")  # clean slate on every run
db.init_db()

today = date.today()
for employee, city, offset, length, purpose in SAMPLE_TRIPS:
    start = today + timedelta(days=offset)
    trip = db.create_trip(employee, city, start.isoformat(), (start + timedelta(days=length - 1)).isoformat(), purpose)
    print("saved:", trip)
