from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class User:
    id: int
    username: str
    email: str
    password: str
    created_at: datetime
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }

@dataclass
class Paper:
    id: int
    user_id: int
    paper_id: str
    title: str
    authors: List[str]
    abstract: str
    summary: Optional[str]
    url: str
    published_date: datetime
    saved_at: datetime
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'paper_id': self.paper_id,
            'title': self.title,
            'authors': self.authors,
            'abstract': self.abstract,
            'summary': self.summary,
            'url': self.url,
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'saved_at': self.saved_at.isoformat()
        }

@dataclass
class Query:
    id: int
    user_id: int
    query_text: str
    created_at: datetime
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'query_text': self.query_text,
            'created_at': self.created_at.isoformat()
        }