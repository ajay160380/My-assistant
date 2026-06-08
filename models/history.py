"""
Command History Module — SQLite-based persistent command history with search.
"""
import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'jarvis_history.db')


def _ensure_db():
    """Create the database and table if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS command_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_input TEXT NOT NULL,
            action TEXT,
            target TEXT,
            value TEXT,
            success INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()


def save_command(user_input, action="", target="", value="", success=True):
    """Save a command to history."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        'INSERT INTO command_history (timestamp, user_input, action, target, value, success) VALUES (?, ?, ?, ?, ?, ?)',
        (datetime.datetime.now().isoformat(), user_input, action, target, value, 1 if success else 0)
    )
    conn.commit()
    conn.close()


def get_history(limit=50, search_query=None):
    """Get command history, optionally filtered by search query."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if search_query:
        rows = conn.execute(
            'SELECT * FROM command_history WHERE user_input LIKE ? ORDER BY id DESC LIMIT ?',
            (f'%{search_query}%', limit)
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT * FROM command_history ORDER BY id DESC LIMIT ?',
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_stats():
    """Get usage statistics."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute('SELECT COUNT(*) FROM command_history').fetchone()[0]
    today = conn.execute(
        'SELECT COUNT(*) FROM command_history WHERE timestamp LIKE ?',
        (datetime.datetime.now().strftime('%Y-%m-%d') + '%',)
    ).fetchone()[0]
    top_actions = conn.execute(
        'SELECT action, COUNT(*) as cnt FROM command_history GROUP BY action ORDER BY cnt DESC LIMIT 5'
    ).fetchall()
    conn.close()
    return {
        'total_commands': total,
        'today_commands': today,
        'top_actions': [{'action': a[0], 'count': a[1]} for a in top_actions]
    }
