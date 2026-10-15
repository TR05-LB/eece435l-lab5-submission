"""SQLite CRUD operations for the Lab 5 user management API."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path


DATABASE_PATH = Path(os.environ.get("LAB5_DATABASE", Path(__file__).with_name("database.db")))
USER_FIELDS = ("name", "email", "phone", "address", "country")


def connect_to_db():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def create_db_table():
    with closing(connect_to_db()) as connection, connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                country TEXT NOT NULL
            )
        """)


def insert_user(user):
    with closing(connect_to_db()) as connection, connection:
        cursor = connection.execute(
            "INSERT INTO users (name, email, phone, address, country) VALUES (?, ?, ?, ?, ?)",
            tuple(user[field] for field in USER_FIELDS),
        )
        row = connection.execute(
            "SELECT * FROM users WHERE user_id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)


def get_users():
    with closing(connect_to_db()) as connection:
        return [dict(row) for row in connection.execute("SELECT * FROM users ORDER BY user_id")]


def get_user_by_id(user_id):
    with closing(connect_to_db()) as connection:
        row = connection.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def update_user(user):
    with closing(connect_to_db()) as connection, connection:
        cursor = connection.execute(
            "UPDATE users SET name = ?, email = ?, phone = ?, address = ?, country = ? WHERE user_id = ?",
            tuple(user[field] for field in USER_FIELDS) + (user["user_id"],),
        )
        if cursor.rowcount == 0:
            return None
        return dict(connection.execute(
            "SELECT * FROM users WHERE user_id = ?", (user["user_id"],)
        ).fetchone())


def delete_user(user_id):
    with closing(connect_to_db()) as connection, connection:
        cursor = connection.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        return cursor.rowcount > 0


if __name__ == "__main__":
    create_db_table()
    print(f"User table ready in {DATABASE_PATH}")
