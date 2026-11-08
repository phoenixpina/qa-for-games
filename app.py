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


@app.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
def edit_project(project_id):
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if name:
            connection.execute(
                "UPDATE projects SET name = ?, description = ? WHERE id = ?",
                (name, description, project_id)
            )
            connection.commit()
        connection.close()
        return redirect(url_for("projects"))

    project = connection.execute(
        "SELECT id, name, description FROM projects WHERE id = ?",
        (project_id,)
    ).fetchone()
    connection.close()

    if project is None:
        return "Project not found", 404
    return render_template("edit_project.html", project=project)


@app.route("/projects/<int:project_id>/delete", methods=["POST"])
def delete_project(project_id):
    connection = sqlite3.connect(DATABASE)
    suite_ids = [row[0] for row in connection.execute(
        "SELECT id FROM test_suites WHERE project_id = ?", (project_id,)
    ).fetchall()]
    test_case_ids = [row[0] for row in connection.execute(
        "SELECT id FROM test_cases WHERE project_id = ?", (project_id,)
    ).fetchall()]

    if test_case_ids:
        placeholders = ",".join("?" for _ in test_case_ids)
        connection.execute(
            f"DELETE FROM defects WHERE test_case_id IN ({placeholders})",
            test_case_ids
        )
        connection.execute(
            f"DELETE FROM test_executions WHERE test_case_id IN ({placeholders})",
            test_case_ids
        )
        connection.execute(
            f"DELETE FROM test_cases WHERE id IN ({placeholders})",
            test_case_ids
        )

    if suite_ids:
        placeholders = ",".join("?" for _ in suite_ids)
        connection.execute(
            f"DELETE FROM test_suites WHERE id IN ({placeholders})",
            suite_ids
        )

    connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    connection.commit()
    connection.close()
    return redirect(url_for("projects"))


@app.route("/test-cases")
def test_cases():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    projects = connection.execute(
        "SELECT id, name FROM projects ORDER BY name"
    ).fetchall()

    suites = connection.execute(
        """
        SELECT test_suites.id, test_suites.project_id, test_suites.name,
               test_suites.description, projects.name AS project_name,
               COUNT(test_cases.id) AS test_case_count
        FROM test_suites
        JOIN projects ON projects.id = test_suites.project_id
        LEFT JOIN test_cases ON test_cases.suite_id = test_suites.id
        GROUP BY test_suites.id
        ORDER BY projects.name, test_suites.name
        """
    ).fetchall()

    unassigned_test_cases = connection.execute(
        """
        SELECT test_cases.id,
               test_cases.title,
               projects.name AS project_name
        FROM test_cases
        JOIN projects ON projects.id = test_cases.project_id
        WHERE test_cases.suite_id IS NULL
        ORDER BY test_cases.id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "test_cases.html",
        projects=projects,
        suites=suites,
        unassigned_test_cases=unassigned_test_cases
    )


@app.route("/suites/<int:suite_id>", methods=["GET", "POST"])
def suite_detail(suite_id):
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    suite = connection.execute(
        """
        SELECT test_suites.id, test_suites.name, test_suites.description,
               projects.name AS project_name
        FROM test_suites
        JOIN projects ON projects.id = test_suites.project_id
        WHERE test_suites.id = ?
        """,
        (suite_id,)
    ).fetchone()

    if suite is None:
        connection.close()
        return "Test suite not found", 404

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        steps = request.form.get("steps", "").strip()
        expected_result = request.form.get("expected_result", "").strip()

        if title and steps and expected_result:
            connection.execute(
                """
                INSERT INTO test_cases
                    (project_id, suite_id, title, steps, expected_result)
                SELECT project_id, ?, ?, ?, ?
                FROM test_suites
                WHERE id = ?
                """,
                (suite_id, title, steps, expected_result, suite_id)
            )
            connection.commit()

        connection.close()
        return redirect(url_for("suite_detail", suite_id=suite_id))

    test_cases = connection.execute(
        """
        SELECT id, title, steps, expected_result
        FROM test_cases
        WHERE suite_id = ?
        ORDER BY id DESC
        """,
        (suite_id,)
    ).fetchall()

    executions = connection.execute(
        """
        SELECT id, test_case_id, result, notes, executed_at
        FROM test_executions
        WHERE test_case_id IN (
            SELECT id FROM test_cases WHERE suite_id = ?
        )
        ORDER BY executed_at DESC, id DESC
        """,
        (suite_id,)
    ).fetchall()

    executions_by_test_case = {}
    for execution in executions:
        executions_by_test_case.setdefault(
            execution["test_case_id"], []
        ).append(execution)

    connection.close()
    return render_template(
        "suite_detail.html",
        suite=suite,
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


@app.route("/suites/<int:suite_id>/edit", methods=["GET", "POST"])
def edit_suite(suite_id):
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if name:
            connection.execute(
                "UPDATE test_suites SET name = ?, description = ? WHERE id = ?",
                (name, description, suite_id)
            )
            connection.commit()
        connection.close()
        return redirect(url_for("suite_detail", suite_id=suite_id))

    suite = connection.execute(
        "SELECT id, name, description FROM test_suites WHERE id = ?",
        (suite_id,)
    ).fetchone()
    connection.close()
    if suite is None:
        return "Test suite not found", 404
    return render_template("edit_suite.html", suite=suite)


@app.route("/suites/<int:suite_id>/delete", methods=["POST"])
def delete_suite(suite_id):
    connection = sqlite3.connect(DATABASE)
    test_case_ids = [row[0] for row in connection.execute(
        "SELECT id FROM test_cases WHERE suite_id = ?", (suite_id,)
    ).fetchall()]

    if test_case_ids:
        placeholders = ",".join("?" for _ in test_case_ids)
        connection.execute(
            f"DELETE FROM defects WHERE test_case_id IN ({placeholders})",
            test_case_ids
        )
        connection.execute(
            f"DELETE FROM test_executions WHERE test_case_id IN ({placeholders})",
            test_case_ids
        )
        connection.execute(
            f"DELETE FROM test_cases WHERE id IN ({placeholders})",
            test_case_ids
        )

    connection.execute("DELETE FROM test_suites WHERE id = ?", (suite_id,))
    connection.commit()
    connection.close()
    return redirect(url_for("test_cases"))


@app.route("/test-cases/<int:test_case_id>/edit", methods=["GET", "POST"])
def edit_test_case(test_case_id):
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        steps = request.form.get("steps", "").strip()
        expected_result = request.form.get("expected_result", "").strip()
        if title and steps and expected_result:
            connection.execute(
                """
                UPDATE test_cases
                SET title = ?, steps = ?, expected_result = ?
                WHERE id = ?
                """,
                (title, steps, expected_result, test_case_id)
            )
            connection.commit()
        suite = connection.execute(
            "SELECT suite_id FROM test_cases WHERE id = ?", (test_case_id,)
        ).fetchone()
        connection.close()
        if suite and suite["suite_id"]:
            return redirect(url_for("suite_detail", suite_id=suite["suite_id"]))
        return redirect(url_for("test_cases"))

    test_case = connection.execute(
        """
        SELECT id, title, steps, expected_result, suite_id
        FROM test_cases WHERE id = ?
        """,
        (test_case_id,)
    ).fetchone()
    connection.close()
    if test_case is None:
        return "Test case not found", 404
    return render_template("edit_test_case.html", test_case=test_case)


@app.route("/test-cases/<int:test_case_id>/delete", methods=["POST"])
def delete_test_case(test_case_id):
    connection = sqlite3.connect(DATABASE)
    test_case = connection.execute(
        "SELECT suite_id FROM test_cases WHERE id = ?", (test_case_id,)
    ).fetchone()
    connection.execute("DELETE FROM defects WHERE test_case_id = ?", (test_case_id,))
    connection.execute("DELETE FROM test_executions WHERE test_case_id = ?", (test_case_id,))
    connection.execute("DELETE FROM test_cases WHERE id = ?", (test_case_id,))
    connection.commit()
    connection.close()
    if test_case and test_case[0]:
        return redirect(url_for("suite_detail", suite_id=test_case[0]))
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

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    test_case = connection.execute(
        "SELECT suite_id FROM test_cases WHERE id = ?",
        (test_case_id,)
    ).fetchone()
    connection.close()

    if test_case and test_case["suite_id"]:
        return redirect(url_for("suite_detail", suite_id=test_case["suite_id"]))
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
               projects.name AS project_name,
               test_suites.name AS suite_name
        FROM test_cases
        JOIN projects ON projects.id = test_cases.project_id
        JOIN test_executions ON test_executions.test_case_id = test_cases.id
        LEFT JOIN test_suites ON test_suites.id = test_cases.suite_id
        WHERE test_executions.result = 'Failed'
        ORDER BY projects.name, test_suites.name, test_cases.title
        """
    ).fetchall()

    defect_suites = connection.execute(
        """
        SELECT test_suites.id, test_suites.name, test_suites.description,
               projects.name AS project_name,
               COUNT(defects.id) AS defect_count
        FROM defects
        JOIN test_cases ON test_cases.id = defects.test_case_id
        JOIN projects ON projects.id = test_cases.project_id
        JOIN test_suites ON test_suites.id = test_cases.suite_id
        GROUP BY test_suites.id
        ORDER BY projects.name, test_suites.name
        """
    ).fetchall()

    unassigned_defects = connection.execute(
        """
        SELECT defects.id, defects.title,
               projects.name AS project_name,
               test_cases.title AS test_case_title
        FROM defects
        JOIN test_cases ON test_cases.id = defects.test_case_id
        JOIN projects ON projects.id = test_cases.project_id
        WHERE test_cases.suite_id IS NULL
        ORDER BY defects.id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "defects.html",
        failed_tests=failed_tests,
        defect_suites=defect_suites,
        unassigned_defects=unassigned_defects
    )


@app.route("/defect-suites/<int:suite_id>")
def defect_suite_detail(suite_id):
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    suite = connection.execute(
        """
        SELECT test_suites.id, test_suites.name, test_suites.description,
               projects.name AS project_name
        FROM test_suites
        JOIN projects ON projects.id = test_suites.project_id
        WHERE test_suites.id = ?
        """,
        (suite_id,)
    ).fetchone()

    if suite is None:
        connection.close()
        return "Test suite not found", 404

    defects = connection.execute(
        """
        SELECT defects.id, defects.title, defects.description,
               defects.reproduction_steps, defects.expected_result,
               defects.actual_result, defects.severity, defects.priority,
               defects.status, defects.created_at,
               test_cases.title AS test_case_title
        FROM defects
        JOIN test_cases ON test_cases.id = defects.test_case_id
        WHERE test_cases.suite_id = ?
        ORDER BY defects.id DESC
        """,
        (suite_id,)
    ).fetchall()

    connection.close()
    return render_template(
        "defect_suite_detail.html",
        suite=suite,
        defects=defects
    )


@app.route("/defects/<int:defect_id>/status", methods=["POST"])
def update_defect_status(defect_id):
    status = request.form.get("status")
    allowed_statuses = {"Open", "In Progress", "Fixed", "Closed"}

    if status in allowed_statuses:
        connection = sqlite3.connect(DATABASE)
        connection.row_factory = sqlite3.Row
        defect = connection.execute(
            """
            SELECT test_cases.suite_id
            FROM defects
            JOIN test_cases ON test_cases.id = defects.test_case_id
            WHERE defects.id = ?
            """,
            (defect_id,)
        ).fetchone()
        connection.execute(
            "UPDATE defects SET status = ? WHERE id = ?",
            (status, defect_id)
        )
        connection.commit()
        connection.close()

        if defect and defect["suite_id"]:
            return redirect(url_for("defect_suite_detail", suite_id=defect["suite_id"]))

    return redirect(url_for("defects"))


@app.route("/defects/<int:defect_id>/edit", methods=["GET", "POST"])
def edit_defect(defect_id):
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        reproduction_steps = request.form.get("reproduction_steps", "").strip()
        expected_result = request.form.get("expected_result", "").strip()
        actual_result = request.form.get("actual_result", "").strip()
        severity = request.form.get("severity")
        priority = request.form.get("priority")
        status = request.form.get("status")

        if (
            title and description and reproduction_steps
            and expected_result and actual_result
            and severity in {"Low", "Medium", "High", "Critical"}
            and priority in {"Low", "Medium", "High"}
            and status in {"Open", "In Progress", "Fixed", "Closed"}
        ):
            connection.execute(
                """
                UPDATE defects
                SET title = ?, description = ?, reproduction_steps = ?,
                    expected_result = ?, actual_result = ?, severity = ?,
                    priority = ?, status = ?
                WHERE id = ?
                """,
                (
                    title, description, reproduction_steps, expected_result,
                    actual_result, severity, priority, status, defect_id
                )
            )
            connection.commit()

        suite = connection.execute(
            """
            SELECT test_cases.suite_id
            FROM defects
            JOIN test_cases ON test_cases.id = defects.test_case_id
            WHERE defects.id = ?
            """,
            (defect_id,)
        ).fetchone()
        connection.close()
        if suite and suite["suite_id"]:
            return redirect(url_for("defect_suite_detail", suite_id=suite["suite_id"]))
        return redirect(url_for("defects"))

    defect = connection.execute(
        """
        SELECT id, title, description, reproduction_steps,
               expected_result, actual_result, severity, priority, status
        FROM defects WHERE id = ?
        """,
        (defect_id,)
    ).fetchone()
    connection.close()
    if defect is None:
        return "Defect not found", 404
    return render_template("edit_defect.html", defect=defect)


@app.route("/defects/<int:defect_id>/delete", methods=["POST"])
def delete_defect(defect_id):
    connection = sqlite3.connect(DATABASE)
    connection.execute("DELETE FROM defects WHERE id = ?", (defect_id,))
    connection.commit()
    connection.close()
    return redirect(url_for("defects"))


@app.route("/executions/<int:execution_id>/edit", methods=["GET", "POST"])
def edit_execution(execution_id):
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    if request.method == "POST":
        result = request.form.get("result")
        notes = request.form.get("notes", "").strip()
        if result in {"Passed", "Failed", "Blocked"}:
            connection.execute(
                "UPDATE test_executions SET result = ?, notes = ? WHERE id = ?",
                (result, notes, execution_id)
            )
            connection.commit()
        execution = connection.execute(
            "SELECT test_case_id FROM test_executions WHERE id = ?",
            (execution_id,)
        ).fetchone()
        test_case = None
        if execution:
            test_case = connection.execute(
                "SELECT suite_id FROM test_cases WHERE id = ?",
                (execution["test_case_id"],)
            ).fetchone()
        connection.close()
        if test_case and test_case["suite_id"]:
            return redirect(url_for("suite_detail", suite_id=test_case["suite_id"]))
        return redirect(url_for("test_cases"))

    execution = connection.execute(
        "SELECT id, result, notes FROM test_executions WHERE id = ?",
        (execution_id,)
    ).fetchone()
    connection.close()
    if execution is None:
        return "Execution result not found", 404
    return render_template("edit_execution.html", execution=execution)


@app.route("/executions/<int:execution_id>/delete", methods=["POST"])
def delete_execution(execution_id):
    connection = sqlite3.connect(DATABASE)
    execution = connection.execute(
        "SELECT test_case_id FROM test_executions WHERE id = ?",
        (execution_id,)
    ).fetchone()
    connection.execute("DELETE FROM test_executions WHERE id = ?", (execution_id,))
    connection.commit()
    test_case = None
    if execution:
        test_case = connection.execute(
            "SELECT suite_id FROM test_cases WHERE id = ?", (execution[0],)
        ).fetchone()
    connection.close()
    if test_case and test_case[0]:
        return redirect(url_for("suite_detail", suite_id=test_case[0]))
    return redirect(url_for("test_cases"))


@app.route("/reports")
def reports():
    return render_template("reports.html")


if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)
