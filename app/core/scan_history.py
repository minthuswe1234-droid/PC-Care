"""SQLite metadata-only history in the user's local application data directory."""
import os
import sqlite3
from pathlib import Path


def database_path():
    base = Path(os.environ.get('LOCALAPPDATA') or Path.home() / '.local' / 'share')
    return base / 'PCCare' / 'history.sqlite3'


def save_scan(result, db=None):
    path = Path(db) if db else database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS scans (id INTEGER PRIMARY KEY, scanned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, root TEXT NOT NULL, files INTEGER NOT NULL, bytes INTEGER NOT NULL, errors INTEGER NOT NULL, partial INTEGER NOT NULL)')
        conn.execute('INSERT INTO scans(root,files,bytes,errors,partial) VALUES(?,?,?,?,?)',
                     (result['root'], result['files'], result['bytes'], result['errors'], int(result['partial'])))


def recent_scans(db=None, limit=15):
    path = Path(db) if db else database_path()
    if not path.exists():
        return []
    with sqlite3.connect(path) as conn:
        return conn.execute('SELECT scanned_at,root,files,bytes,errors,partial FROM scans ORDER BY id DESC LIMIT ?', (min(max(limit, 1), 100),)).fetchall()
