import sqlite3
from pathlib import Path


DATABASE = Path(__file__).parent / "qa_for_games.db"


def initialize_database():
    connection = sqlite3.connect(DATABASE)

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            steps TEXT NOT NULL,
            expected_result TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
        """
    )

    connection.commit()
    connection.close()


if __name__ == "__main__":
    initialize_database()
    print(f"Database created or updated: {DATABASE.name}")