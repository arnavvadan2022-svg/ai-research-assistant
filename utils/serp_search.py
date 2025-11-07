"""
SERP API Search Integration
Provides web search capabilities using SERP API for quantum-related queries.
"""

import requests
from typing import List, Dict
from config import Config


class SerpSearch:
    def __init__(self):
        self.api_key = Config.SERP_API_KEY
        self.base_url = "https://serpapi.com/search"
        
    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search the web using SERP API.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of search results with snippets and sources
        """
        if not self.api_key:
            print("⚠️ SERP API key not configured")
            return []
        
        try:
            # Add quantum context to query for better results
            enhanced_query = f"{query} quantum computing quantum mechanics"
            
            params = {
                'q': enhanced_query,
                'api_key': self.api_key,
                'num': min(max_results, 10),  # SERP API limit
                'engine': 'google'
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # Extract organic results
            organic_results = data.get('organic_results', [])
            
            for result in organic_results[:max_results]:
                results.append({
                    'title': result.get('title', ''),
                    'link': result.get('link', ''),
                    'snippet': result.get('snippet', ''),
                    'source': self._extract_domain(result.get('link', '')),
                    'position': result.get('position', 0)
                })
            
            # Also check for answer box (featured snippet)
            answer_box = data.get('answer_box', {})
            if answer_box:
                answer_result = {
                    'title': answer_box.get('title', 'Featured Answer'),
                    'link': answer_box.get('link', ''),
                    'snippet': answer_box.get('answer', answer_box.get('snippet', '')),
                    'source': self._extract_domain(answer_box.get('link', '')),
                    'position': 0,
                    'is_featured': True
                }
                results.insert(0, answer_result)
            
            print(f"✅ Found {len(results)} web results via SERP API")
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"❌ SERP API error: {str(e)}")
            return []
        except Exception as e:
            print(f"❌ Error processing SERP results: {str(e)}")
            return []
    
    def _extract_domain(self, url: str) -> str:
        """
        Extract domain name from URL.
        
        Args:
            url: Full URL
            
        Returns:
            Domain name
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove 'www.' prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return url
    
    def format_results_for_context(self, results: List[Dict]) -> str:
        """
        Format search results as context for the AI model.
        
        Args:
            results: List of search results
            
        Returns:
            Formatted string for model context
        """
        if not results:
            return "No web search results available."
        
        context = "Web Search Results:\n\n"
        for i, result in enumerate(results, 1):
            context += f"{i}. {result['title']}\n"
            context += f"   Source: {result['source']}\n"
            context += f"   {result['snippet']}\n\n"
        
        return context
