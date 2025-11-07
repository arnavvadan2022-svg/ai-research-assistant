"""
Quantum Computing and Quantum Mechanics Chatbot Module

This module provides a specialized chatbot for quantum computing and quantum mechanics
queries. It validates queries, searches arXiv for quantum papers, performs web searches
via SerpAPI, and synthesizes comprehensive responses.
"""

import re
from typing import Dict, List, Optional, Tuple
import logging
from config import Config
from utils.paper_search import PaperSearch

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuantumChatbot:
    """
    A specialized chatbot for quantum computing and quantum mechanics topics.
    """
    
    # Quantum computing and quantum mechanics keywords
    QUANTUM_KEYWORDS = {
        # Quantum Computing
        'quantum', 'qubit', 'qubits', 'superposition', 'entanglement', 
        'quantum computing', 'quantum computer', 'quantum algorithm',
        'quantum gate', 'quantum circuit', 'quantum error correction',
        'quantum supremacy', 'quantum advantage', 'quantum annealing',
        'adiabatic quantum', 'topological quantum', 'quantum simulation',
        'variational quantum', 'vqe', 'qaoa', 'quantum machine learning',
        'quantum cryptography', 'quantum communication', 'quantum internet',
        'quantum teleportation', 'quantum key distribution', 'qkd',
        'quantum sensor', 'quantum metrology', 'quantum imaging',
        
        # Quantum Mechanics
        'quantum mechanics', 'quantum physics', 'quantum theory',
        'wave function', 'wavefunction', 'schrodinger', 'schrödinger',
        'heisenberg', 'uncertainty principle', 'pauli', 'dirac',
        'fermion', 'boson', 'spin', 'angular momentum', 'orbital',
        'quantum state', 'quantum operator', 'hamiltonian',
        'eigenvalue', 'eigenstate', 'quantum field theory', 'qft',
        'quantum electrodynamics', 'qed', 'quantum chromodynamics', 'qcd',
        'photon', 'phonon', 'quantum harmonic oscillator',
        'quantum tunneling', 'quantum coherence', 'decoherence',
        'quantum measurement', 'quantum observable', 'quantum system',
        'hilbert space', 'density matrix', 'quantum correlations',
        'bell inequality', 'bell state', 'quantum nonlocality',
        'quantum contextuality', 'quantum foundations',
        
        # Quantum Hardware
        'superconducting qubit', 'transmon', 'flux qubit',
        'ion trap', 'trapped ion', 'quantum dot', 'topological qubit',
        'majorana', 'photonic qubit', 'quantum processor',
        'quantum chip', 'dilution refrigerator', 'cryogenic',
        
        # Quantum Software/Algorithms
        'shor', "shor's algorithm", 'grover', "grover's algorithm",
        'quantum fourier transform', 'qft', 'phase estimation',
        'amplitude amplification', 'quantum walk', 'quantum search',
        'quantum optimization', 'vqe', 'variational quantum eigensolver',
        'qaoa', 'quantum approximate optimization',
        'qiskit', 'cirq', 'pennylane', 'quantum programming',
    }
    
    def __init__(self):
        """Initialize the quantum chatbot."""
        self.paper_search = PaperSearch()
        self.serpapi_key = Config.SERPAPI_API_KEY
        logger.info("Quantum Chatbot initialized")
    
    def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a query is related to quantum computing or quantum mechanics.
        
        Args:
            query: The user's query string
            
        Returns:
            Tuple of (is_valid, reason)
            - is_valid: True if query is quantum-related, False otherwise
            - reason: Explanation message if query is not valid, None if valid
        """
        if not query or not query.strip():
            return False, "Query cannot be empty"
        
        # Convert to lowercase for case-insensitive matching
        query_lower = query.lower()
        
        # Check if any quantum keyword is present in the query
        for keyword in self.QUANTUM_KEYWORDS:
            if keyword in query_lower:
                logger.info(f"Query validated: Contains quantum keyword '{keyword}'")
                return True, None
        
        # If no quantum keyword found, reject the query
        reason = (
            "This chatbot specializes in quantum computing and quantum mechanics topics. "
            "Your query does not appear to be related to these domains. "
            "Please ask questions about quantum computing, quantum algorithms, "
            "quantum mechanics, quantum hardware, or related quantum topics."
        )
        logger.info(f"Query rejected: Not quantum-related")
        return False, reason
    
    def search_quantum_papers(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search for quantum-related research papers from arXiv.
        Specifically targets the quant-ph (quantum physics) category.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of paper dictionaries
        """
        try:
            # Enhance query with quantum physics category filter for arXiv
            # The quant-ph category covers quantum physics papers
            enhanced_query = f'cat:quant-ph AND ({query})'
            
            logger.info(f"Searching arXiv with query: {enhanced_query}")
            papers = self.paper_search.search(enhanced_query, max_results)
            
            logger.info(f"Found {len(papers)} quantum papers from arXiv")
            return papers
        except Exception as e:
            logger.error(f"Error searching quantum papers: {str(e)}")
            return []
    
    def search_web(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Search the web using SerpAPI for current information.
        
        Args:
            query: Search query
            num_results: Number of web results to return
            
        Returns:
            List of search result dictionaries
        """
        if not self.serpapi_key:
            logger.warning("SerpAPI key not configured, skipping web search")
            return []
        
        try:
            from serpapi import GoogleSearch
            
            params = {
                "q": query + " quantum computing OR quantum mechanics",
                "api_key": self.serpapi_key,
                "num": num_results,
                "engine": "google"
            }
            
            logger.info(f"Searching web via SerpAPI: {query}")
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Extract organic results
            web_results = []
            if "organic_results" in results:
                for result in results["organic_results"][:num_results]:
                    web_results.append({
                        "title": result.get("title", ""),
                        "link": result.get("link", ""),
                        "snippet": result.get("snippet", ""),
                        "source": result.get("source", "")
                    })
            
            logger.info(f"Found {len(web_results)} web results")
            return web_results
        except ImportError:
            logger.error("google-search-results package not installed")
            return []
        except Exception as e:
            logger.error(f"Error searching web: {str(e)}")
            return []
    
    def synthesize_response(
        self, 
        query: str, 
        papers: List[Dict], 
        web_results: List[Dict]
    ) -> Dict:
        """
        Synthesize a comprehensive response from papers and web results.
        
        Args:
            query: The original user query
            papers: List of research papers
            web_results: List of web search results
            
        Returns:
            Dictionary containing the synthesized response
        """
        response = {
            "query": query,
            "answer": "",
            "papers": papers,
            "web_results": web_results,
            "sources_count": {
                "papers": len(papers),
                "web_results": len(web_results)
            }
        }
        
        # Build comprehensive answer
        answer_parts = []
        
        # Introduction
        answer_parts.append(
            f"Based on your query about '{query}', here's what I found from "
            f"quantum computing and quantum mechanics research:"
        )
        answer_parts.append("")
        
        # Paper summary
        if papers:
            answer_parts.append(f"📚 **Research Papers ({len(papers)} found):**")
            answer_parts.append("")
            
            for i, paper in enumerate(papers[:3], 1):  # Show top 3 papers
                answer_parts.append(f"{i}. **{paper['title']}**")
                answer_parts.append(f"   Authors: {', '.join(paper['authors'][:3])}")
                
                # Create a brief snippet from abstract
                abstract = paper.get('abstract', '')
                if len(abstract) > 200:
                    snippet = abstract[:200] + "..."
                else:
                    snippet = abstract
                answer_parts.append(f"   Summary: {snippet}")
                answer_parts.append(f"   [Read more]({paper['url']})")
                answer_parts.append("")
            
            if len(papers) > 3:
                answer_parts.append(f"   ... and {len(papers) - 3} more papers available")
                answer_parts.append("")
        else:
            answer_parts.append("📚 **Research Papers:** No arXiv papers found for this specific query.")
            answer_parts.append("")
        
        # Web results summary
        if web_results:
            answer_parts.append(f"🌐 **Web Resources ({len(web_results)} found):**")
            answer_parts.append("")
            
            for i, result in enumerate(web_results[:3], 1):  # Show top 3 results
                answer_parts.append(f"{i}. **{result['title']}**")
                answer_parts.append(f"   {result['snippet']}")
                answer_parts.append(f"   Source: [{result.get('source', 'Web')}]({result['link']})")
                answer_parts.append("")
            
            if len(web_results) > 3:
                answer_parts.append(f"   ... and {len(web_results) - 3} more resources available")
                answer_parts.append("")
        else:
            if not self.serpapi_key:
                answer_parts.append(
                    "🌐 **Web Resources:** Web search not available "
                    "(SerpAPI key not configured)"
                )
            else:
                answer_parts.append("🌐 **Web Resources:** No web results found.")
            answer_parts.append("")
        
        # Conclusion
        if papers or web_results:
            answer_parts.append(
                "💡 **Key Insights:** The resources above provide comprehensive "
                "information about your quantum computing/mechanics query. "
                "Research papers offer peer-reviewed academic insights, while web "
                "resources provide current developments and practical information."
            )
        else:
            answer_parts.append(
                "⚠️ No specific resources found for this query. "
                "Try rephrasing your question or using different quantum-related keywords."
            )
        
        response["answer"] = "\n".join(answer_parts)
        
        logger.info(f"Synthesized response with {len(papers)} papers and {len(web_results)} web results")
        return response
    
    def process_query(
        self, 
        query: str, 
        max_papers: int = 10, 
        max_web_results: int = 5
    ) -> Dict:
        """
        Process a quantum computing/mechanics query end-to-end.
        
        Args:
            query: User's query
            max_papers: Maximum number of papers to retrieve
            max_web_results: Maximum number of web results to retrieve
            
        Returns:
            Dictionary containing the complete response or error
        """
        try:
            # Step 1: Validate query
            is_valid, reason = self.validate_query(query)
            if not is_valid:
                logger.warning(f"Query validation failed: {reason}")
                return {
                    "success": False,
                    "error": reason,
                    "query": query
                }
            
            # Step 2: Search research papers
            papers = self.search_quantum_papers(query, max_papers)
            
            # Step 3: Search web
            web_results = self.search_web(query, max_web_results)
            
            # Step 4: Synthesize response
            response = self.synthesize_response(query, papers, web_results)
            response["success"] = True
            
            logger.info(f"Successfully processed query: {query}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                "success": False,
                "error": f"An error occurred while processing your query: {str(e)}",
                "query": query
            }
