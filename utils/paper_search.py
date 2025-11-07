import requests
import feedparser
from datetime import datetime
from typing import List, Dict
import re
from config import Config


class PaperSearch:
    def __init__(self):
        self.arxiv_api_url = 'http://export.arxiv.org/api/query'
        self.quantum_categories = Config.QUANTUM_CATEGORIES
    
    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search for quantum physics research papers on arXiv.
        Focused on quantum computing and quantum mechanics categories.
        """
        try:
            # Build category filter for quantum-related papers
            category_filter = ' OR '.join([f'cat:{cat}' for cat in self.quantum_categories])
            
            # Combine query with quantum category filter
            search_query = f'({query}) AND ({category_filter})'
            
            # Prepare query parameters
            params = {
                'search_query': search_query,
                'start': 0,
                'max_results': max_results,
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            
            # Make request to arXiv API
            response = requests.get(self.arxiv_api_url, params=params, timeout=15)
            response.raise_for_status()
            
            # Parse the response
            feed = feedparser.parse(response.content)
            
            papers = []
            for entry in feed.entries:
                paper = {
                    'id': self._extract_arxiv_id(entry.id),
                    'title': entry.title,
                    'authors': [author.name for author in entry.authors],
                    'abstract': entry.summary,
                    'url': entry.link,
                    'published': entry.published,
                    'updated': entry.updated,
                    'categories': [tag.term for tag in entry.tags] if hasattr(entry, 'tags') else [],
                    'pdf_url': self._get_pdf_url(entry)
                }
                papers.append(paper)
            
            print(f"✅ Found {len(papers)} quantum papers from arXiv")
            return papers
        except Exception as e:
            print(f"❌ Error searching arXiv papers: {str(e)}")
            return []
    
    def _extract_arxiv_id(self, arxiv_url: str) -> str:
        """Extract arXiv ID from URL"""
        match = re.search(r'(\d+\.\d+)', arxiv_url)
        return match.group(1) if match else arxiv_url
    
    def _get_pdf_url(self, entry) -> str:
        """Get PDF URL from entry"""
        for link in entry.links:
            if link.get('type') == 'application/pdf':
                return link.href
        return entry.link.replace('/abs/', '/pdf/')
    
    def get_paper_details(self, arxiv_id: str) -> Dict:
        """
        Get detailed information about a specific paper.
        """
        try:
            params = {
                'id_list': arxiv_id
            }
            
            response = requests.get(self.arxiv_api_url, params=params, timeout=10)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            if feed.entries:
                entry = feed.entries[0]
                return {
                    'id': self._extract_arxiv_id(entry.id),
                    'title': entry.title,
                    'authors': [author.name for author in entry.authors],
                    'abstract': entry.summary,
                    'url': entry.link,
                    'published': entry.published,
                    'updated': entry.updated,
                    'categories': [tag.term for tag in entry.tags] if hasattr(entry, 'tags') else [],
                    'pdf_url': self._get_pdf_url(entry)
                }
            return None
        except Exception as e:
            print(f"❌ Error getting paper details: {str(e)}")
            return None
    
    def format_papers_for_context(self, papers: List[Dict]) -> str:
        """
        Format papers as context for the AI model.
        
        Args:
            papers: List of arXiv papers
            
        Returns:
            Formatted string for model context
        """
        if not papers:
            return "No arXiv papers found."
        
        context = "arXiv Research Papers:\n\n"
        for i, paper in enumerate(papers, 1):
            authors_str = ", ".join(paper['authors'][:3])
            if len(paper['authors']) > 3:
                authors_str += " et al."
            
            context += f"{i}. {paper['title']}\n"
            context += f"   Authors: {authors_str}\n"
            context += f"   arXiv ID: {paper['id']}\n"
            context += f"   Abstract: {paper['abstract'][:300]}...\n\n"
        
        return context
