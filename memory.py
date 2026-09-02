import sqlite3
import os
from datetime import datetime


class TroyMemory:
    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Cria as tabelas se não existirem."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT NOT NULL,
                    project     TEXT,
                    user_input  TEXT NOT NULL,
                    troy_output TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    project          TEXT PRIMARY KEY,
                    summary          TEXT,
                    where_we_stopped TEXT,
                    last_updated     TEXT NOT NULL
                )
            """)
            conn.commit()

    def save_conversation(self, user_input, troy_output, project=None):
        """Salva uma conversa no banco."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO conversations (timestamp, project, user_input, troy_output) VALUES (?, ?, ?, ?)",
                (timestamp, project, user_input, troy_output),
            )
            conn.commit()
        return timestamp

    def update_conversation_project(self, conversation_id, project):
        """Atualiza o projeto de uma conversa já salva (usado pelo categorizer em background)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE conversations SET project = ? WHERE id = ?",
                (project, conversation_id),
            )
            conn.commit()

    def get_last_conversation_id(self):
        """Retorna o ID da última conversa inserida."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT MAX(id) FROM conversations").fetchone()
            return row[0] if row else None

    def save_checkpoint(self, project, summary, where_we_stopped):
        """Cria ou atualiza o checkpoint de um projeto."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO checkpoints (project, summary, where_we_stopped, last_updated)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(project) DO UPDATE SET
                       summary = excluded.summary,
                       where_we_stopped = excluded.where_we_stopped,
                       last_updated = excluded.last_updated
                """,
                (project, summary, where_we_stopped, timestamp),
            )
            conn.commit()

    def get_checkpoint(self, project):
        """Retorna o checkpoint de um projeto ou None."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM checkpoints WHERE project = ?", (project,)
            ).fetchone()
            return dict(row) if row else None

    def get_all_projects(self):
        """Retorna lista de todos os projetos que existem nos checkpoints."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT project FROM checkpoints").fetchall()
            return [r[0] for r in rows]

    def get_recent_conversations(self, limit=5, project=None):
        """Retorna as últimas N conversas. Se project for dado, filtra por projeto."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if project:
                rows = conn.execute(
                    "SELECT * FROM conversations WHERE project = ? ORDER BY id DESC LIMIT ?",
                    (project, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM conversations ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in reversed(rows)]  # cronológico

    def search_conversations(self, query, limit=5):
        """Busca conversas por texto (LIKE)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT * FROM conversations
                   WHERE user_input LIKE ? OR troy_output LIKE ?
                   ORDER BY id DESC LIMIT ?""",
                (f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            return [dict(r) for r in reversed(rows)]
