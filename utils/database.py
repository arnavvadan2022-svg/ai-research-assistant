import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
import json


class Database:
    def __init__(self):
        self.db_path = 'research_assistant.db'
        self.connection = None

    def get_connection(self):
        """Get database connection"""
        if not self.connection:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
        return self.connection

    def init_db(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create papers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                paper_id TEXT NOT NULL,
                title TEXT NOT NULL,
                authors TEXT,
                abstract TEXT,
                summary TEXT,
                url TEXT,
                published_date TIMESTAMP,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, paper_id)
            )
        """)

        # Create queries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                query_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Create knowledge_graphs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_graphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                source_text TEXT,
                source_paper_id TEXT,
                graph_data TEXT NOT NULL,
                entity_count INTEGER DEFAULT 0,
                relation_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Create kg_datasets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kg_datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                kg_id INTEGER,
                dataset_data TEXT NOT NULL,
                format TEXT NOT NULL,
                sample_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (kg_id) REFERENCES knowledge_graphs(id) ON DELETE CASCADE
            )
        """)

        conn.commit()
        print("Database initialized successfully!")

    def create_user(self, username: str, email: str, password: str) -> int:
        """Create a new user"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, password)
        )

        user_id = cursor.lastrowid
        conn.commit()

        return user_id

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        return dict(user) if user else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()

        return dict(user) if user else None

    def save_paper(self, user_id: int, paper_id: str, paper_data: Dict) -> int:
        """Save a paper"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO papers (user_id, paper_id, title, authors, abstract, summary, url, published_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            paper_id,
            paper_data.get('title'),
            json.dumps(paper_data.get('authors', [])),
            paper_data.get('abstract'),
            paper_data.get('summary'),
            paper_data.get('url'),
            paper_data.get('published_date')
        ))

        paper_db_id = cursor.lastrowid
        conn.commit()

        return paper_db_id

    def get_user_papers(self, user_id: int) -> List[Dict]:
        """Get all papers for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM papers WHERE user_id = ? ORDER BY saved_at DESC",
            (user_id,)
        )

        papers = cursor.fetchall()

        return [dict(paper) for paper in papers]

    def delete_paper(self, user_id: int, paper_id: str):
        """Delete a paper"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM papers WHERE user_id = ? AND id = ?",
            (user_id, paper_id)
        )

        conn.commit()

    def save_query(self, user_id: int, query_text: str):
        """Save a search query"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO queries (user_id, query_text) VALUES (?, ?)",
            (user_id, query_text)
        )

        conn.commit()

    def get_query_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get query history for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM queries WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )

        queries = cursor.fetchall()

        return [dict(query) for query in queries]

    # ── Knowledge-Graph operations ───────────────────────────────────────────

    def save_knowledge_graph(
        self,
        user_id: int,
        source_text: str,
        graph_data: str,
        entity_count: int,
        relation_count: int,
        source_paper_id: str = None,
    ) -> int:
        """Persist a built KG; returns the new row ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO knowledge_graphs
               (user_id, source_text, source_paper_id, graph_data,
                entity_count, relation_count)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, source_text, source_paper_id, graph_data,
             entity_count, relation_count),
        )
        kg_id = cursor.lastrowid
        conn.commit()
        return kg_id

    def get_user_knowledge_graphs(self, user_id: int) -> List[Dict]:
        """Return all KGs saved by a user (graph_data excluded for list view)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, user_id, source_paper_id, entity_count,
                      relation_count, created_at
               FROM knowledge_graphs
               WHERE user_id = ?
               ORDER BY created_at DESC""",
            (user_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_knowledge_graph(self, user_id: int, kg_id: int) -> Optional[Dict]:
        """Return a single KG row including the full graph_data JSON."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM knowledge_graphs WHERE id = ? AND user_id = ?",
            (kg_id, user_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_knowledge_graph(self, user_id: int, kg_id: int):
        """Delete a KG and its associated datasets."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM knowledge_graphs WHERE id = ? AND user_id = ?",
            (kg_id, user_id),
        )
        conn.commit()

    # ── Dataset operations ───────────────────────────────────────────────────

    def save_kg_dataset(
        self,
        user_id: int,
        kg_id: int,
        dataset_data: str,
        fmt: str,
        sample_count: int,
    ) -> int:
        """Persist a generated training dataset; returns new row ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO kg_datasets
               (user_id, kg_id, dataset_data, format, sample_count)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, kg_id, dataset_data, fmt, sample_count),
        )
        ds_id = cursor.lastrowid
        conn.commit()
        return ds_id

    def get_user_datasets(self, user_id: int) -> List[Dict]:
        """Return all datasets for a user (dataset_data excluded)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, user_id, kg_id, format, sample_count, created_at
               FROM kg_datasets
               WHERE user_id = ?
               ORDER BY created_at DESC""",
            (user_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_kg_dataset(self, user_id: int, dataset_id: int) -> Optional[Dict]:
        """Return a single dataset row including full dataset_data."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM kg_datasets WHERE id = ? AND user_id = ?",
            (dataset_id, user_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()