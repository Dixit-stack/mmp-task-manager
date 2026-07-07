import sqlite3
from flask import Flask, request, redirect, session, render_template_string, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-to-a-random-string-before-submitting"
DB = "app.db"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB)
    with open("schema.sql") as f:
        db.executescript(f.read())
    db.commit()
    db.close()


LAYOUT = """
<!doctype html><title>Task Manager</title>
<h2>Task Manager MVP</h2>
{% if session.user_id %}
  <p>Logged in as {{ session.name }} ({{ session.role }}) | <a href="/logout">Logout</a></p>
{% endif %}
<hr>{{ body|safe }}
"""

REGISTER = """
<h3>Register</h3>
<form method="post">
Name: <input name="full_name" required><br>
Email: <input name="email" type="email" required><br>
Password: <input name="password" type="password" required><br>
<button type="submit">Register</button>
</form>
<p><a href="/login">Already have an account? Login</a></p>
"""

LOGIN = """
<h3>Login</h3>
<form method="post">
Email: <input name="email" type="email" required><br>
Password: <input name="password" type="password" required><br>
<button type="submit">Login</button>
</form>
{% if error %}<p style="color:red">{{ error }}</p>{% endif %}
<p><a href="/register">No account? Register</a></p>
"""

TASKS = """
<h3>Your Tasks</h3>
<form method="post" action="/tasks/add">
New task: <input name="title" required>
<button type="submit">Add</button>
</form>
<ul>
{% for t in tasks %}
  <li>[{{ t.status }}] {{ t.title }}
    <form style="display:inline" method="post" action="/tasks/{{ t.task_id }}/done">
      <button type="submit">Mark done</button>
    </form>
    <form style="display:inline" method="post" action="/tasks/{{ t.task_id }}/delete">
      <button type="submit">Delete</button>
    </form>
  </li>
{% endfor %}
</ul>
"""


def render(body, **kw):
    return render_template_string(LAYOUT, body=render_template_string(body, **kw))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        pw_hash = generate_password_hash(password)

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (role_id, full_name, email, password_hash) "
                "VALUES ((SELECT role_id FROM roles WHERE role_name='member'), ?, ?, ?)",
                (full_name, email, pw_hash),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return render(LOGIN, error="Email already registered.")
        return redirect("/login")
    return render(REGISTER)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT u.*, r.role_name FROM users u "
            "JOIN roles r ON r.role_id = u.role_id WHERE u.email = ?",
            (email,),
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["user_id"]
            session["name"] = user["full_name"]
            session["role"] = user["role_name"]
            return redirect("/tasks")
        return render(LOGIN, error="Invalid email or password.")
    return render(LOGIN)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


def require_login():
    return "user_id" in session


@app.route("/tasks")
def tasks():
    if not require_login():
        return redirect("/login")
    db = get_db()
    rows = db.execute(
        "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC",
        (session["user_id"],),
    ).fetchall()
    return render(TASKS, tasks=rows)


@app.route("/tasks/add", methods=["POST"])
def add_task():
    if not require_login():
        return redirect("/login")
    title = request.form["title"].strip()
    if title:
        db = get_db()
        db.execute(
            "INSERT INTO tasks (user_id, title) VALUES (?, ?)",
            (session["user_id"], title),
        )
        db.commit()
    return redirect("/tasks")


@app.route("/tasks/<int:task_id>/done", methods=["POST"])
def complete_task(task_id):
    if not require_login():
        return redirect("/login")
    db = get_db()
    db.execute(
        "UPDATE tasks SET status='done' WHERE task_id=? AND user_id=?",
        (task_id, session["user_id"]),
    )
    db.commit()
    return redirect("/tasks")


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
def delete_task(task_id):
    if not require_login():
        return redirect("/login")
    db = get_db()
    db.execute(
        "DELETE FROM tasks WHERE task_id=? AND user_id=?",
        (task_id, session["user_id"]),
    )
    db.commit()
    return redirect("/tasks")


@app.route("/")
def index():
    return redirect("/tasks") if require_login() else redirect("/login")


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)