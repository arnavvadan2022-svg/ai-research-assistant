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

        # Create conversation sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Create conversation messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
    # Conversation management methods
    def create_conversation_session(self, user_id: int) -> str:
        """Create a new conversation session"""
        import uuid
        conn = self.get_connection()
        cursor = conn.cursor()
        
        session_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO conversation_sessions (id, user_id) VALUES (?, ?)",
            (session_id, user_id)
        )
        conn.commit()
        return session_id
    
    def save_conversation_message(self, session_id: str, user_id: int, 
                                   role: str, content: str, sources: List[Dict] = None) -> int:
        """Save a conversation message"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        sources_json = json.dumps(sources) if sources else None
        
        cursor.execute("""
            INSERT INTO conversation_messages (session_id, user_id, role, content, sources)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, user_id, role, content, sources_json))
        
        # Update session last activity
        cursor.execute(
            "UPDATE conversation_sessions SET last_activity = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,)
        )
        
        message_id = cursor.lastrowid
        conn.commit()
        return message_id
    
    def get_conversation_history(self, session_id: str, user_id: int, limit: int = 10) -> List[Dict]:
        """Get conversation history for a session"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM conversation_messages 
            WHERE session_id = ? AND user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (session_id, user_id, limit))
        
        messages = cursor.fetchall()
        result = []
        for msg in reversed(messages):  # Reverse to get chronological order
            msg_dict = dict(msg)
            if msg_dict.get('sources'):
                msg_dict['sources'] = json.loads(msg_dict['sources'])
            result.append(msg_dict)
        
        return result
    
    def get_user_sessions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get all conversation sessions for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.*, 
                   (SELECT COUNT(*) FROM conversation_messages WHERE session_id = s.id) as message_count
            FROM conversation_sessions s
            WHERE user_id = ? 
            ORDER BY last_activity DESC 
            LIMIT ?
        """, (user_id, limit))
        
        sessions = cursor.fetchall()
        return [dict(session) for session in sessions]
    
    def delete_conversation_session(self, session_id: str, user_id: int) -> bool:
        """Delete a conversation session"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM conversation_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id)
        )
        
        conn.commit()
        return cursor.rowcount > 0
