"""
Conversation Manager
Manages chat sessions and conversation context for the quantum assistant.
"""

from typing import List, Dict, Optional
from datetime import datetime
import json


class ConversationManager:
    def __init__(self, database):
        """
        Initialize conversation manager with database connection.
        
        Args:
            database: Database instance
        """
        self.db = database
        self.max_history = 10  # Maximum number of messages to keep in context
    
    def add_message(self, session_id: str, user_id: int, role: str, 
                    content: str, sources: Optional[List[Dict]] = None) -> int:
        """
        Add a message to the conversation.
        
        Args:
            session_id: Unique session identifier
            user_id: User ID
            role: 'user' or 'assistant'
            content: Message content
            sources: Optional list of sources (papers/web results)
            
        Returns:
            Message ID
        """
        return self.db.save_conversation_message(
            session_id, user_id, role, content, sources
        )
    
    def get_conversation_history(self, session_id: str, user_id: int, 
                                 limit: Optional[int] = None) -> List[Dict]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            user_id: User ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of conversation messages
        """
        if limit is None:
            limit = self.max_history
        
        return self.db.get_conversation_history(session_id, user_id, limit)
    
    def get_context_for_model(self, session_id: str, user_id: int, 
                              max_messages: int = 5) -> str:
        """
        Get formatted conversation context for the AI model.
        
        Args:
            session_id: Session identifier
            user_id: User ID
            max_messages: Maximum number of previous messages to include
            
        Returns:
            Formatted conversation context string
        """
        history = self.get_conversation_history(session_id, user_id, max_messages)
        
        if not history:
            return ""
        
        context = "Previous conversation:\n"
        for msg in history:
            role_label = "User" if msg['role'] == 'user' else "Assistant"
            context += f"{role_label}: {msg['content']}\n"
        
        return context
    
    def create_session(self, user_id: int) -> str:
        """
        Create a new conversation session.
        
        Args:
            user_id: User ID
            
        Returns:
            Session ID
        """
        return self.db.create_conversation_session(user_id)
    
    def get_user_sessions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Get all conversation sessions for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of sessions to retrieve
            
        Returns:
            List of session information
        """
        return self.db.get_user_sessions(user_id, limit)
    
    def delete_session(self, session_id: str, user_id: int) -> bool:
        """
        Delete a conversation session.
        
        Args:
            session_id: Session identifier
            user_id: User ID
            
        Returns:
            True if deleted successfully
        """
        return self.db.delete_conversation_session(session_id, user_id)
    
    def format_sources(self, arxiv_papers: List[Dict], 
                      web_results: List[Dict]) -> List[Dict]:
        """
        Format sources for storage and display.
        
        Args:
            arxiv_papers: List of arXiv papers
            web_results: List of web search results
            
        Returns:
            Combined list of formatted sources
        """
        sources = []
        
        # Add arXiv papers
        for paper in arxiv_papers:
            sources.append({
                'type': 'arxiv',
                'id': paper.get('id', ''),
                'title': paper.get('title', ''),
                'url': paper.get('url', ''),
                'citation': f"[arXiv:{paper.get('id', '')}]"
            })
        
        # Add web results
        for result in web_results:
            sources.append({
                'type': 'web',
                'title': result.get('title', ''),
                'url': result.get('link', ''),
                'source': result.get('source', ''),
                'citation': f"[Source: {result.get('source', 'Web')}]"
            })
        
        return sources
