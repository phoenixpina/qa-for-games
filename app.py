from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/projects")
def projects():
    return render_template("projects.html")


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
    app.run(debug=True)
