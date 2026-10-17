import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from database import DATABASE, initialize_database

app = Flask(__name__)


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/projects", methods=["GET", "POST"])
def projects():
    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form["description"].strip()

        if name:
            connection = sqlite3.connect(DATABASE)
            connection.execute(
                "INSERT INTO projects (name, description) VALUES (?, ?)",
                (name, description)
            )
            connection.commit()
            connection.close()

        return redirect(url_for("projects"))

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    projects = connection.execute(
        "SELECT id, name, description FROM projects ORDER BY id DESC"
    ).fetchall()
    connection.close()

    return render_template("projects.html", projects=projects)


@app.route("/test-cases")
def test_cases():
    return render_template("test_cases.html")


@app.route("/defects")
def defects():
    return render_template("defects.html")


@app.route("/reports")
def reports():
    return render_template("reports.html")


if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)