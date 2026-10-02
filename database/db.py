import sqlite3
import os

DB_FILE = "outreach.db"


def get_connection():
    return sqlite3.connect(DB_FILE)


def initialize_db():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outreach (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            channel_name TEXT,
            email_subject TEXT,
            email_body TEXT,
            instagram_dm TEXT,
            status TEXT DEFAULT 'Generated',
            sent_at TEXT,
            error_message TEXT
        )
    """)

    conn.commit()
    conn.close()


def get_outreach(email):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM outreach
        WHERE email = ?
        """,
        (email,)
    )

    result = cursor.fetchone()

    conn.close()

    return result


def save_generated(
    email,
    channel_name,
    email_subject,
    email_body,
    instagram_dm
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO outreach
        (
            email,
            channel_name,
            email_subject,
            email_body,
            instagram_dm,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            email,
            channel_name,
            email_subject,
            email_body,
            instagram_dm,
            "Generated"
        )
    )

    conn.commit()
    conn.close()


def mark_sent(email):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE outreach
        SET status = 'Sent',
            sent_at = datetime('now')
        WHERE email = ?
        """,
        (email,)
    )

    conn.commit()
    conn.close()


def mark_failed(email, error_message):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE outreach
        SET status = 'Failed',
            error_message = ?
        WHERE email = ?
        """,
        (
            error_message,
            email
        )
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":

    initialize_db()

    print(
        "Database initialized successfully."
    )