"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import json
import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

DB_PATH = Path(__file__).with_name("activities.db")

DEFAULT_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
}

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static")


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL,
                participants TEXT NOT NULL DEFAULT '[]'
            )
            """
        )

        rows = connection.execute("SELECT name FROM activities").fetchall()
        if not rows:
            connection.executemany(
                """
                INSERT INTO activities (name, description, schedule, max_participants, participants)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        name,
                        details["description"],
                        details["schedule"],
                        details["max_participants"],
                        json.dumps(details["participants"]),
                    )
                    for name, details in DEFAULT_ACTIVITIES.items()
                ],
            )
        connection.commit()


def _activity_from_row(row):
    return {
        "description": row["description"],
        "schedule": row["schedule"],
        "max_participants": row["max_participants"],
        "participants": json.loads(row["participants"] or "[]"),
    }


def get_activities_store():
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM activities ORDER BY name").fetchall()
        return {
            row["name"]: _activity_from_row(row)
            for row in rows
        }


def get_activity_or_404(activity_name: str):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    return _activity_from_row(row)


def save_activity(activity_name: str, activity_data: dict):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO activities (name, description, schedule, max_participants, participants)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                description = excluded.description,
                schedule = excluded.schedule,
                max_participants = excluded.max_participants,
                participants = excluded.participants
            """,
            (
                activity_name,
                activity_data["description"],
                activity_data["schedule"],
                activity_data["max_participants"],
                json.dumps(activity_data["participants"]),
            ),
        )
        connection.commit()


init_db()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return get_activities_store()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    activity = get_activity_or_404(activity_name)
    participants = activity["participants"]

    if email in participants:
        raise HTTPException(status_code=400, detail="Student is already signed up")

    if len(participants) >= activity["max_participants"]:
        raise HTTPException(status_code=400, detail="Activity is full")

    participants.append(email)
    activity["participants"] = participants
    save_activity(activity_name, activity)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    activity = get_activity_or_404(activity_name)
    participants = activity["participants"]

    if email not in participants:
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    participants.remove(email)
    activity["participants"] = participants
    save_activity(activity_name, activity)
    return {"message": f"Unregistered {email} from {activity_name}"}
