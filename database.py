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

    connection.commit()
    connection.close()


if __name__ == "__main__":
    initialize_database()
    print(f"Database created or updated: {DATABASE.name}")