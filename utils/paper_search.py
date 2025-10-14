import requests
import feedparser
from datetime import datetime
from typing import List, Dict
import re

class PaperSearch:
    def __init__(self):
        self.arxiv_api_url = 'http://export.arxiv.org/api/query'
    
    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search for research papers on arXiv
        """
        try:
            # Prepare query parameters
            params = {
                'search_query': f'all:{query}',
                'start': 0,
                'max_results': max_results,
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            
            # Make request to arXiv API
            response = requests.get(self.arxiv_api_url, params=params)
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
            
            return papers
        except Exception as e:
            print(f"Error searching papers: {str(e)}")
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
        Get detailed information about a specific paper
        """
        try:
            params = {
                'id_list': arxiv_id
            }
            
            response = requests.get(self.arxiv_api_url, params=params)
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
            print(f"Error getting paper details: {str(e)}")
            return None