"""
Quantum AI Processor
Uses Hugging Face models to generate answers to quantum computing and quantum mechanics questions.
Combines information from arXiv papers and web search results.
"""

import os
from typing import Dict, List
import requests
from config import Config


class QuantumAIProcessor:
    def __init__(self):
        self.api_key = Config.HUGGINGFACE_API_KEY
        self.model_name = Config.HF_MODEL
        self.hf_api_url = f"https://api-inference.huggingface.co/models/{self.model_name}"
        print(f"✅ Quantum AI Processor initialized (model: {self.model_name})")
    
    def generate_answer(self, question: str, arxiv_context: str, 
                       web_context: str, conversation_context: str = "") -> str:
        """
        Generate an answer to a quantum question using both arXiv and web sources.
        
        Args:
            question: User's quantum question
            arxiv_context: Context from arXiv papers
            web_context: Context from web search
            conversation_context: Previous conversation context
            
        Returns:
            Generated answer
        """
        # Build comprehensive prompt
        prompt = self._build_prompt(question, arxiv_context, web_context, conversation_context)
        
        # Try Hugging Face API first
        if self.api_key:
            try:
                answer = self._hf_api_generate(prompt)
                if answer:
                    return answer
            except Exception as e:
                print(f"⚠️ Hugging Face API error: {e}")
        
        # Fallback to smart extraction if API fails
        return self._smart_answer(question, arxiv_context, web_context)
    
    def _build_prompt(self, question: str, arxiv_context: str, 
                     web_context: str, conversation_context: str) -> str:
        """
        Build a comprehensive prompt for the model.
        """
        prompt = "You are a quantum computing and quantum mechanics expert assistant. "
        prompt += "Answer the following question using the provided research papers and web sources.\n\n"
        
        if conversation_context:
            prompt += f"{conversation_context}\n\n"
        
        if arxiv_context and arxiv_context != "No arXiv papers found.":
            prompt += f"{arxiv_context}\n\n"
        
        if web_context and web_context != "No web search results available.":
            prompt += f"{web_context}\n\n"
        
        prompt += f"Question: {question}\n\n"
        prompt += "Provide a comprehensive answer that:\n"
        prompt += "1. Directly answers the question\n"
        prompt += "2. Incorporates information from the research papers and web sources\n"
        prompt += "3. Is accurate and scientifically sound\n"
        prompt += "4. Is clear and understandable\n\n"
        prompt += "Answer:"
        
        return prompt
    
    def _hf_api_generate(self, prompt: str) -> str:
        """
        Generate answer using Hugging Face Inference API.
        """
        # Limit prompt length
        max_prompt_length = 1500
        if len(prompt) > max_prompt_length:
            # Truncate while keeping the question
            parts = prompt.split("Question:")
            if len(parts) == 2:
                context = parts[0][:max_prompt_length - 300]
                prompt = context + "Question:" + parts[1]
            else:
                prompt = prompt[:max_prompt_length]
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 400,
                "temperature": 0.7,
                "top_p": 0.95,
                "do_sample": True
            }
        }
        
        response = requests.post(
            self.hf_api_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0].get('generated_text', '')
                # Extract only the answer part (after "Answer:")
                if 'Answer:' in generated_text:
                    answer = generated_text.split('Answer:')[-1].strip()
                    return answer
                return generated_text
            elif isinstance(result, dict):
                return result.get('generated_text', '').split('Answer:')[-1].strip()
        
        # If model is loading
        if response.status_code == 503:
            print("⏳ Model is loading, using smart answer generation...")
        
        return None
    
    def _smart_answer(self, question: str, arxiv_context: str, web_context: str) -> str:
        """
        Generate a smart answer by extracting and combining information.
        """
        answer = "Based on the available sources:\n\n"
        
        # Extract key information from arXiv papers
        if arxiv_context and "No arXiv papers found" not in arxiv_context:
            answer += "📚 From Research Papers:\n"
            # Extract abstracts
            abstracts = self._extract_abstracts(arxiv_context)
            if abstracts:
                answer += abstracts[:500] + "...\n\n"
        
        # Extract key information from web results
        if web_context and "No web search results" not in web_context:
            answer += "🌐 From Web Sources:\n"
            snippets = self._extract_snippets(web_context)
            if snippets:
                answer += snippets[:500] + "...\n\n"
        
        if "📚" not in answer and "🌐" not in answer:
            answer = "I apologize, but I couldn't find sufficient information to answer your quantum question. "
            answer += "This might be because:\n"
            answer += "1. The topic is very specialized or recent\n"
            answer += "2. The search didn't return relevant results\n\n"
            answer += "Please try rephrasing your question or asking about a different quantum topic."
        else:
            answer += "\n💡 Note: For more detailed AI-generated answers, please configure a HUGGINGFACE_API_KEY."
        
        return answer
    
    def _extract_abstracts(self, arxiv_context: str) -> str:
        """Extract and combine abstracts from arXiv context."""
        lines = arxiv_context.split('\n')
        abstracts = []
        
        for i, line in enumerate(lines):
            if 'Abstract:' in line:
                abstract = line.split('Abstract:')[-1].strip()
                abstracts.append(abstract)
        
        return ' '.join(abstracts)
    
    def _extract_snippets(self, web_context: str) -> str:
        """Extract snippets from web context."""
        lines = web_context.split('\n')
        snippets = []
        
        for line in lines:
            line = line.strip()
            # Skip headers and source lines
            if line and not line.startswith('Web Search') and not line.startswith('Source:') and not line.endswith(':'):
                # Skip numbered lines
                if not (len(line) > 0 and line[0].isdigit() and '. ' in line[:5]):
                    snippets.append(line)
        
        return ' '.join(snippets)
    
    def format_answer_with_citations(self, answer: str, sources: List[Dict]) -> str:
        """
        Format answer with inline citations.
        
        Args:
            answer: Generated answer
            sources: List of sources used
            
        Returns:
            Answer with citations
        """
        formatted_answer = answer + "\n\n"
        
        if sources:
            formatted_answer += "📖 Sources:\n"
            
            arxiv_sources = [s for s in sources if s['type'] == 'arxiv']
            web_sources = [s for s in sources if s['type'] == 'web']
            
            if arxiv_sources:
                formatted_answer += "\nResearch Papers:\n"
                for source in arxiv_sources:
                    formatted_answer += f"  • {source['title']} [{source['citation']}]\n"
                    formatted_answer += f"    {source['url']}\n"
            
            if web_sources:
                formatted_answer += "\nWeb Resources:\n"
                for source in web_sources:
                    formatted_answer += f"  • {source['title']} [{source['citation']}]\n"
                    formatted_answer += f"    {source['url']}\n"
        
        return formatted_answer
