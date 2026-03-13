from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

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


@dataclass
class KGEntity:
    text: str
    entity_type: str
    confidence: float
    occurrences: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            'text':        self.text,
            'type':        self.entity_type,
            'confidence':  self.confidence,
            'occurrences': self.occurrences,
        }


@dataclass
class KGRelation:
    subject: str
    subject_type: str
    predicate: str
    object: str
    object_type: str
    confidence: float
    sentence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'subject':      self.subject,
            'subject_type': self.subject_type,
            'predicate':    self.predicate,
            'object':       self.object,
            'object_type':  self.object_type,
            'confidence':   self.confidence,
            'sentence':     self.sentence,
        }


@dataclass
class KnowledgeGraph:
    id: int
    user_id: int
    source_text: str
    graph_data: Dict[str, Any]
    entity_count: int
    relation_count: int
    source_paper_id: Optional[str]
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id':              self.id,
            'user_id':         self.user_id,
            'source_paper_id': self.source_paper_id,
            'graph_data':      self.graph_data,
            'entity_count':    self.entity_count,
            'relation_count':  self.relation_count,
            'created_at':      self.created_at.isoformat(),
        }


@dataclass
class KGDataset:
    id: int
    user_id: int
    kg_id: int
    dataset_data: str
    format: str
    sample_count: int
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id':           self.id,
            'user_id':      self.user_id,
            'kg_id':        self.kg_id,
            'format':       self.format,
            'sample_count': self.sample_count,
            'created_at':   self.created_at.isoformat(),
        }