import sqlite3
from pathlib import Path


DATABASE = Path(__file__).parent / "qa_for_games.db"


def initialize_database():
    connection = sqlite3.connect(DATABASE)

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS test_suites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            steps TEXT NOT NULL,
            expected_result TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'Medium'
                CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
        """
    )

    test_case_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(test_cases)").fetchall()
    }
    if "suite_id" not in test_case_columns:
        connection.execute(
            "ALTER TABLE test_cases ADD COLUMN suite_id INTEGER"
        )

    if "priority" not in test_case_columns:
        connection.execute(
            """
            ALTER TABLE test_cases
            ADD COLUMN priority TEXT NOT NULL DEFAULT 'Medium'
                CHECK (priority IN ('Low', 'Medium', 'High', 'Critical'))
            """
        )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS test_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_case_id INTEGER NOT NULL,
            result TEXT NOT NULL CHECK (result IN ('Passed', 'Failed', 'Blocked')),
            notes TEXT,
            executed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (test_case_id) REFERENCES test_cases (id)
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS defects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_case_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            reproduction_steps TEXT NOT NULL,
            expected_result TEXT NOT NULL,
            actual_result TEXT NOT NULL,
            severity TEXT NOT NULL CHECK (severity IN ('Low', 'Medium', 'High', 'Critical')),
            priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High')),
            status TEXT NOT NULL DEFAULT 'Open'
                CHECK (status IN ('Open', 'In Progress', 'Fixed', 'Closed')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (test_case_id) REFERENCES test_cases (id)
        )
        """
    )

    connection.commit()
    connection.close()


if __name__ == "__main__":
    initialize_database()
    print(f"Database created or updated: {DATABASE.name}")
