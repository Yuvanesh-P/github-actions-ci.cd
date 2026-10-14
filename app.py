import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-demo-key")
app.config["DATABASE"] = os.environ.get(
    "DATABASE_PATH", os.path.join(os.path.dirname(__file__), "tasks.db")
)

STATUSES = ["To Do", "In Progress", "Done"]
PRIORITIES = ["Low", "Medium", "High"]


def get_db():
    db = sqlite3.connect(app.config["DATABASE"])
    db.row_factory = sqlite3.Row
    return db


def init_db():
    path = app.config["DATABASE"]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'Medium',
                status TEXT NOT NULL DEFAULT 'To Do',
                due_date TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


init_db()


@app.get("/")
def dashboard():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "All")
    priority = request.args.get("priority", "All")

    where, params = [], []
    if search:
        where.append("(title LIKE ? OR description LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if status in STATUSES:
        where.append("status = ?")
        params.append(status)
    if priority in PRIORITIES:
        where.append("priority = ?")
        params.append(priority)

    sql = "SELECT * FROM tasks"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC"

    with get_db() as db:
        tasks = db.execute(sql, params).fetchall()
        counts = {
            row["status"]: row["total"]
            for row in db.execute(
                "SELECT status, COUNT(*) AS total FROM tasks GROUP BY status"
            ).fetchall()
        }
        total = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

    stats = {
        "total": total,
        "todo": counts.get("To Do", 0),
        "progress": counts.get("In Progress", 0),
        "done": counts.get("Done", 0),
    }

    return render_template(
        "index.html", tasks=tasks, stats=stats,
        statuses=STATUSES, priorities=PRIORITIES,
        selected_status=status, selected_priority=priority, search=search
    )


@app.post("/tasks")
def create_task():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    priority = request.form.get("priority", "Medium")
    due_date = request.form.get("due_date", "").strip()

    if not title or len(title) > 120 or len(description) > 1000:
        flash("Enter a valid title and description.", "error")
        return redirect(url_for("dashboard"))
    if priority not in PRIORITIES:
        flash("Choose a valid priority.", "error")
        return redirect(url_for("dashboard"))

    with get_db() as db:
        db.execute(
            "INSERT INTO tasks (title, description, priority, due_date) VALUES (?, ?, ?, ?)",
            (title, description, priority, due_date)
        )
    flash("Task created successfully.", "success")
    return redirect(url_for("dashboard"))


@app.post("/tasks/<int:task_id>/status")
def update_status(task_id):
    status = request.form.get("status", "")
    if status not in STATUSES:
        flash("Invalid task status.", "error")
        return redirect(url_for("dashboard"))

    with get_db() as db:
        result = db.execute(
            "UPDATE tasks SET status = ? WHERE id = ?", (status, task_id)
        )
    flash("Task status updated." if result.rowcount else "Task not found.",
          "success" if result.rowcount else "error")
    return redirect(url_for("dashboard"))


@app.post("/tasks/<int:task_id>/delete")
def delete_task(task_id):
    with get_db() as db:
        result = db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    flash("Task deleted." if result.rowcount else "Task not found.",
          "success" if result.rowcount else "error")
    return redirect(url_for("dashboard"))


@app.get("/health")
def health():
    try:
        with get_db() as db:
            db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}, 200
    except sqlite3.Error:
        return {"status": "unhealthy"}, 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
