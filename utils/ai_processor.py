import os
from typing import Dict
import requests
from config import Config


class AIProcessor:
    def __init__(self):
        self.api_key = Config.OPENAI_API_KEY
        self.hf_api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
        print("✅ AI Processor initialized (using free Hugging Face API)")

    def summarize(self, text: str, max_length: int = 500) -> str:
        """
        Generate a summary using free AI or smart extraction
        """
        # Try OpenAI if key exists
        if self.api_key:
            try:
                return self._openai_summarize(text, max_length)
            except:
                pass

        # Try free Hugging Face API
        try:
            return self._huggingface_api_summarize(text, max_length)
        except Exception as e:
            print(f"Hugging Face API unavailable, using smart extraction: {e}")
            return self._smart_summarize(text, max_length)

    def _openai_summarize(self, text: str, max_length: int) -> str:
        """OpenAI summarization (requires API key)"""
        import openai
        openai.api_key = self.api_key

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",
                 "content": "You are a research assistant that summarizes academic papers concisely."},
                {"role": "user",
                 "content": f"Summarize this research paper abstract in {max_length} characters or less:\n\n{text}"}
            ],
            max_tokens=200,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    def _huggingface_api_summarize(self, text: str, max_length: int) -> str:
        """
        Use FREE Hugging Face Inference API (no installation needed!)
        """
        # Limit input text (API has limits)
        input_text = text[:1024] if len(text) > 1024 else text

        # Call free public API
        response = requests.post(
            self.hf_api_url,
            headers={"Content-Type": "application/json"},
            json={
                "inputs": input_text,
                "parameters": {
                    "max_length": min(max_length, 150),
                    "min_length": 30,
                    "do_sample": False
                }
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()

            # Handle different response formats
            if isinstance(result, list) and len(result) > 0:
                summary = result[0].get('summary_text', '')
                if summary:
                    return f"🤖 AI-Powered Summary:\n\n{summary}"
            elif isinstance(result, dict):
                summary = result.get('summary_text', '')
                if summary:
                    return f"🤖 AI-Powered Summary:\n\n{summary}"

        # If API returns error or is loading
        if response.status_code == 503:
            print("⏳ AI model is loading, using smart extraction...")

        # Fallback to smart extraction
        return self._smart_summarize(text, max_length)

    def _smart_summarize(self, text: str, max_length: int) -> str:
        """
        Smart extractive summarization (always works!)
        """
        if len(text) <= max_length:
            return text

        # Split into sentences
        sentences = []
        for s in text.replace('! ', '!|').replace('? ', '?|').replace('. ', '.|').split('|'):
            s = s.strip()
            if s and len(s) > 10:  # Filter out very short fragments
                sentences.append(s)

        if not sentences:
            return text[:max_length] + "..."

        # Score sentences based on importance
        scored = []
        for i, sentence in enumerate(sentences):
            score = 0

            # First and last sentences are usually important
            if i == 0:
                score += 5
            if i == len(sentences) - 1:
                score += 2

            # Look for key academic terms
            important_words = [
                'propose', 'present', 'show', 'demonstrate', 'find', 'discover',
                'result', 'conclude', 'method', 'approach', 'novel', 'new',
                'significant', 'improve', 'performance', 'achieve', 'develop',
                'introduce', 'study', 'research', 'analysis', 'model', 'algorithm'
            ]

            sentence_lower = sentence.lower()
            for word in important_words:
                if word in sentence_lower:
                    score += 2

            # Prefer medium-length sentences (not too short or too long)
            length = len(sentence)
            if 40 < length < 200:
                score += 2
            elif length < 20:
                score -= 1

            scored.append((sentence, score))

        # Sort by score (highest first)
        scored.sort(key=lambda x: x[1], reverse=True)

        # Build summary with highest-scoring sentences
        summary = ""
        used_sentences = []

        for sentence, score in scored:
            if len(summary) + len(sentence) + 2 <= max_length:
                used_sentences.append(sentence)
                summary += sentence + " "
            if len(summary) >= max_length * 0.85:  # Stop at 85% of max
                break

        # Add prefix to indicate it's smart extraction
        result = summary.strip()
        if result:
            return f"📝 Smart Summary:\n\n{result}"

        return sentences[0] + "..."

    def analyze(self, text: str, analysis_type: str = 'general') -> Dict:
        """
        Perform smart analysis on the research paper
        """
        if self.api_key:
            try:
                return self._openai_analyze(text, analysis_type)
            except:
                pass

        return self._smart_analyze(text, analysis_type)

    def _openai_analyze(self, text: str, analysis_type: str) -> Dict:
        """OpenAI analysis (requires API key)"""
        import openai
        openai.api_key = self.api_key

        prompts = {
            'general': "Analyze this research paper and provide key insights, methodology, and findings.",
            'methodology': "Explain the methodology used in this research paper.",
            'findings': "Summarize the key findings and results of this research paper.",
            'implications': "Discuss the implications and potential applications of this research."
        }

        prompt = prompts.get(analysis_type, prompts['general'])

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a research assistant that analyzes academic papers."},
                {"role": "user", "content": f"{prompt}\n\nPaper abstract:\n{text}"}
            ],
            max_tokens=500,
            temperature=0.7
        )

        return {
            'type': analysis_type,
            'content': response.choices[0].message.content.strip(),
            'model': 'gpt-3.5-turbo'
        }

    def _smart_analyze(self, text: str, analysis_type: str) -> Dict:
        """Smart analysis using keyword extraction and sentence scoring"""
        keywords = self.extract_keywords(text, 15)
        sentences = [s.strip() for s in text.replace('. ', '.|').split('|') if s.strip()]

        # Extract key sentences
        key_sentences = self._extract_key_sentences(sentences, 4)

        analysis_templates = {
            'general': f"""
📊 General Analysis

🔑 Key Terms Identified:
{', '.join(keywords[:10])}

📋 Main Points:
{key_sentences}

💡 This analysis uses smart extraction. For AI-powered deep analysis, add an OpenAI API key.
            """,
            'methodology': f"""
📊 Methodology Analysis

🔬 Identified Keywords:
{', '.join([k for k in keywords if k in ['method', 'approach', 'model', 'algorithm', 'technique', 'system', 'framework']][:5] or keywords[:5])}

📝 Key Methodological Points:
{key_sentences}

💡 For detailed methodology analysis, consider adding an OpenAI API key.
            """,
            'findings': f"""
📊 Findings Analysis

🔍 Key Result Terms:
{', '.join([k for k in keywords if k in ['result', 'performance', 'achieve', 'improve', 'show', 'demonstrate']][:5] or keywords[:5])}

📈 Main Findings:
{key_sentences}

💡 For in-depth findings analysis, consider adding an OpenAI API key.
            """,
            'implications': f"""
📊 Implications Analysis

🎯 Key Concept Terms:
{', '.join(keywords[:8])}

💭 Potential Implications:
{key_sentences}

💡 For detailed implications analysis, consider adding an OpenAI API key.
            """
        }

        content = analysis_templates.get(analysis_type, analysis_templates['general'])

        return {
            'type': analysis_type,
            'content': content.strip(),
            'model': 'smart-extraction'
        }

    def _extract_key_sentences(self, sentences: list, count: int = 3) -> str:
        """Extract the most important sentences"""
        if len(sentences) <= count:
            return '\n'.join([f"• {s}" for s in sentences if s])

        # Score sentences
        scored = []
        for i, sentence in enumerate(sentences):
            score = 1.0 / (i + 1)  # Earlier sentences are more important
            if len(sentence) > 30:  # Prefer longer, more informative sentences
                score += 0.5
            scored.append((sentence, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        return '\n'.join([f"• {s[0]}" for s in scored[:count]])

    def extract_keywords(self, text: str, num_keywords: int = 10) -> list:
        """
        Extract keywords from text
        """
        words = text.lower().split()

        # Expanded stop words list
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
            'these', 'those', 'then', 'than', 'when', 'where', 'why', 'how',
            'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
            'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
            'too', 'very', 'just', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'under', 'again',
            'further', 'once', 'here', 'there', 'who', 'what', 'which', 'whom',
            'whose', 'if', 'because', 'while', 'out', 'up', 'down', 'off', 'over',
            'also', 'its', 'our', 'their', 'your', 'his', 'her', 'them', 'us'
        }

        # Clean and filter words
        keywords = []
        for word in words:
            # Remove punctuation
            word = ''.join(c for c in word if c.isalnum())
            if word and word not in stop_words and len(word) > 3:
                keywords.append(word)

        # Count frequency
        word_count = {}
        for word in keywords:
            word_count[word] = word_count.get(word, 0) + 1

        # Sort by frequency
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)

        return [word for word, count in sorted_words[:num_keywords]]