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
        suite_id = request.form["suite_id"]
        title = request.form["title"].strip()
        steps = request.form["steps"].strip()
        expected_result = request.form["expected_result"].strip()

        connection = sqlite3.connect(DATABASE)
        suite_belongs_to_project = connection.execute(
            "SELECT 1 FROM test_suites WHERE id = ? AND project_id = ?",
            (suite_id, project_id)
        ).fetchone()

        if title and steps and expected_result and suite_belongs_to_project:
            connection.execute(
                """
                INSERT INTO test_cases
                    (project_id, suite_id, title, steps, expected_result)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project_id, suite_id, title, steps, expected_result)
            )
            connection.commit()

        connection.close()

        return redirect(url_for("test_cases"))

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    projects = connection.execute(
        "SELECT id, name FROM projects ORDER BY name"
    ).fetchall()

    suites = connection.execute(
        """
        SELECT test_suites.id, test_suites.project_id, test_suites.name,
               projects.name AS project_name
        FROM test_suites
        JOIN projects ON projects.id = test_suites.project_id
        ORDER BY projects.name, test_suites.name
        """
    ).fetchall()

    test_cases = connection.execute(
        """
        SELECT test_cases.id,
               test_cases.title,
               test_cases.steps,
               test_cases.expected_result,
               projects.name AS project_name,
               test_suites.name AS suite_name
        FROM test_cases
        JOIN projects ON projects.id = test_cases.project_id
        LEFT JOIN test_suites ON test_suites.id = test_cases.suite_id
        ORDER BY test_cases.id DESC
        """
    ).fetchall()

    executions = connection.execute(
        """
        SELECT id, test_case_id, result, notes, executed_at
        FROM test_executions
        ORDER BY executed_at DESC, id DESC
        """
    ).fetchall()

    executions_by_test_case = {}
    for execution in executions:
        executions_by_test_case.setdefault(execution["test_case_id"], []).append(execution)

    connection.close()

    return render_template(
        "test_cases.html",
        projects=projects,
        suites=suites,
        test_cases=test_cases,
        executions_by_test_case=executions_by_test_case
    )


@app.route("/suites", methods=["POST"])
def create_suite():
    project_id = request.form.get("project_id")
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if project_id and name:
        connection = sqlite3.connect(DATABASE)
        connection.execute(
            """
            INSERT INTO test_suites (project_id, name, description)
            VALUES (?, ?, ?)
            """,
            (project_id, name, description)
        )
        connection.commit()
        connection.close()

    return redirect(url_for("test_cases"))


@app.route("/test-cases/<int:test_case_id>/execute", methods=["POST"])
def execute_test_case(test_case_id):
    result = request.form.get("result")
    notes = request.form.get("notes", "").strip()
    allowed_results = {"Passed", "Failed", "Blocked"}

    if result in allowed_results:
        connection = sqlite3.connect(DATABASE)
        connection.execute(
            """
            INSERT INTO test_executions (test_case_id, result, notes)
            VALUES (?, ?, ?)
            """,
            (test_case_id, result, notes)
        )
        connection.commit()
        connection.close()

    return redirect(url_for("test_cases"))


@app.route("/defects", methods=["GET", "POST"])
def defects():
    if request.method == "POST":
        test_case_id = request.form.get("test_case_id")
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        reproduction_steps = request.form.get("reproduction_steps", "").strip()
        expected_result = request.form.get("expected_result", "").strip()
        actual_result = request.form.get("actual_result", "").strip()
        severity = request.form.get("severity")
        priority = request.form.get("priority")

        allowed_severities = {"Low", "Medium", "High", "Critical"}
        allowed_priorities = {"Low", "Medium", "High"}

        if (
            test_case_id and title and description and reproduction_steps
            and expected_result and actual_result
            and severity in allowed_severities
            and priority in allowed_priorities
        ):
            connection = sqlite3.connect(DATABASE)
            connection.execute(
                """
                INSERT INTO defects (
                    test_case_id, title, description, reproduction_steps,
                    expected_result, actual_result, severity, priority
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    test_case_id,
                    title,
                    description,
                    reproduction_steps,
                    expected_result,
                    actual_result,
                    severity,
                    priority,
                )
            )
            connection.commit()
            connection.close()

        return redirect(url_for("defects"))

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    failed_tests = connection.execute(
        """
        SELECT DISTINCT test_cases.id, test_cases.title,
               projects.name AS project_name
        FROM test_cases
        JOIN projects ON projects.id = test_cases.project_id
        JOIN test_executions ON test_executions.test_case_id = test_cases.id
        WHERE test_executions.result = 'Failed'
        ORDER BY projects.name, test_cases.title
        """
    ).fetchall()

    saved_defects = connection.execute(
        """
        SELECT defects.id, defects.title, defects.description,
               defects.reproduction_steps, defects.expected_result,
               defects.actual_result, defects.severity, defects.priority,
               defects.status, defects.created_at,
               test_cases.title AS test_case_title,
               projects.name AS project_name
        FROM defects
        JOIN test_cases ON test_cases.id = defects.test_case_id
        JOIN projects ON projects.id = test_cases.project_id
        ORDER BY defects.id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "defects.html",
        failed_tests=failed_tests,
        defects=saved_defects
    )


@app.route("/defects/<int:defect_id>/status", methods=["POST"])
def update_defect_status(defect_id):
    status = request.form.get("status")
    allowed_statuses = {"Open", "In Progress", "Fixed", "Closed"}

    if status in allowed_statuses:
        connection = sqlite3.connect(DATABASE)
        connection.execute(
            "UPDATE defects SET status = ? WHERE id = ?",
            (status, defect_id)
        )
        connection.commit()
        connection.close()

    return redirect(url_for("defects"))


@app.route("/reports")
def reports():
    return render_template("reports.html")


if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)
