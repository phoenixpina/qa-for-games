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


@app.route("/test-cases", methods=["GET", "POST"])
def test_cases():
    if request.method == "POST":
        project_id = request.form["project_id"]
        title = request.form["title"].strip()
        steps = request.form["steps"].strip()
        expected_result = request.form["expected_result"].strip()

        if title and steps and expected_result:
            connection = sqlite3.connect(DATABASE)
            connection.execute(
                """
                INSERT INTO test_cases
                    (project_id, title, steps, expected_result)
                VALUES (?, ?, ?, ?)
                """,
                (project_id, title, steps, expected_result)
            )
            connection.commit()
            connection.close()

        return redirect(url_for("test_cases"))

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    projects = connection.execute(
        "SELECT id, name FROM projects ORDER BY name"
    ).fetchall()

    test_cases = connection.execute(
        """
        SELECT test_cases.title,
               test_cases.steps,
               test_cases.expected_result,
               projects.name AS project_name
        FROM test_cases
        JOIN projects ON projects.id = test_cases.project_id
        ORDER BY test_cases.id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "test_cases.html",
        projects=projects,
        test_cases=test_cases
    )


@app.route("/defects")
def defects():
    return render_template("defects.html")


@app.route("/reports")
def reports():
    return render_template("reports.html")


if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)