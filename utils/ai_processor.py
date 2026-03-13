import os
from typing import Dict
import requests
from config import Config


class AIProcessor:
    def __init__(self):
        self.groq_api_key = Config.GROQ_API_KEY
        self.groq_model = Config.GROQ_MODEL
        self.openai_api_key = Config.OPENAI_API_KEY
        self.hf_api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
        if self.groq_api_key:
            print("✅ AI Processor initialized (using Groq API)")
        else:
            print("✅ AI Processor initialized (using free Hugging Face API)")

    # ------------------------------------------------------------------
    # Groq helpers
    # ------------------------------------------------------------------

    def _groq_chat(self, system_prompt: str, user_prompt: str, max_tokens: int = 512) -> str:
        """Send a chat request to the Groq API and return the text response."""
        from groq import Groq
        client = Groq(api_key=self.groq_api_key)
        completion = client.chat.completions.create(
            model=self.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return completion.choices[0].message.content.strip()

    # ------------------------------------------------------------------
    # Summarisation
    # ------------------------------------------------------------------

    def summarize(self, text: str, max_length: int = 500) -> str:
        """Generate a summary using Groq (preferred), then OpenAI, then HF."""
        if self.groq_api_key:
            try:
                return self._groq_summarize(text, max_length)
            except Exception as e:
                print(f"Groq summarization failed, falling back: {e}")

        if self.openai_api_key:
            try:
                return self._openai_summarize(text, max_length)
            except Exception:
                pass

        try:
            return self._huggingface_api_summarize(text, max_length)
        except Exception as e:
            print(f"Hugging Face API unavailable, using smart extraction: {e}")
            return self._smart_summarize(text, max_length)

    def _groq_summarize(self, text: str, max_length: int) -> str:
        """Groq-powered summarisation."""
        summary = self._groq_chat(
            system_prompt="You are a research assistant that summarizes academic papers concisely.",
            user_prompt=f"Summarize this research paper abstract in {max_length} characters or less:\n\n{text}",
            max_tokens=300,
        )
        return f"🤖 Groq AI Summary:\n\n{summary}"

    def _openai_summarize(self, text: str, max_length: int) -> str:
        """OpenAI summarization (requires API key)"""
        import openai
        openai.api_key = self.openai_api_key

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
        """Use FREE Hugging Face Inference API (no installation needed!)"""
        input_text = text[:1024] if len(text) > 1024 else text

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

            if isinstance(result, list) and len(result) > 0:
                summary = result[0].get('summary_text', '')
                if summary:
                    return f"🤖 AI-Powered Summary:\n\n{summary}"
            elif isinstance(result, dict):
                summary = result.get('summary_text', '')
                if summary:
                    return f"🤖 AI-Powered Summary:\n\n{summary}"

        if response.status_code == 503:
            print("⏳ AI model is loading, using smart extraction...")

        return self._smart_summarize(text, max_length)

    def _smart_summarize(self, text: str, max_length: int) -> str:
        """Smart extractive summarization (always works!)"""
        if len(text) <= max_length:
            return text

        sentences = []
        for s in text.replace('! ', '!|').replace('? ', '?|').replace('. ', '.|').split('|'):
            s = s.strip()
            if s and len(s) > 10:
                sentences.append(s)

        if not sentences:
            return text[:max_length] + "..."

        scored = []
        for i, sentence in enumerate(sentences):
            score = 0

            if i == 0:
                score += 5
            if i == len(sentences) - 1:
                score += 2

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

            length = len(sentence)
            if 40 < length < 200:
                score += 2
            elif length < 20:
                score -= 1

            scored.append((sentence, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        summary = ""
        used_sentences = []

        for sentence, score in scored:
            if len(summary) + len(sentence) + 2 <= max_length:
                used_sentences.append(sentence)
                summary += sentence + " "
            if len(summary) >= max_length * 0.85:
                break

        result = summary.strip()
        if result:
            return f"📝 Smart Summary:\n\n{result}"

        return sentences[0] + "..."

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyze(self, text: str, analysis_type: str = 'general') -> Dict:
        """Perform analysis on the research paper using Groq (preferred)."""
        if self.groq_api_key:
            try:
                return self._groq_analyze(text, analysis_type)
            except Exception as e:
                print(f"Groq analysis failed, falling back: {e}")

        if self.openai_api_key:
            try:
                return self._openai_analyze(text, analysis_type)
            except Exception:
                pass

        return self._smart_analyze(text, analysis_type)

    def _groq_analyze(self, text: str, analysis_type: str) -> Dict:
        """Groq-powered analysis."""
        prompts = {
            'general': "Analyze this research paper and provide key insights, methodology, and findings.",
            'methodology': "Explain the methodology used in this research paper.",
            'findings': "Summarize the key findings and results of this research paper.",
            'implications': "Discuss the implications and potential applications of this research."
        }
        prompt = prompts.get(analysis_type, prompts['general'])
        content = self._groq_chat(
            system_prompt="You are a research assistant that analyzes academic papers.",
            user_prompt=f"{prompt}\n\nPaper abstract:\n{text}",
            max_tokens=600,
        )
        return {
            'type': analysis_type,
            'content': content,
            'model': self.groq_model,
        }

    def _openai_analyze(self, text: str, analysis_type: str) -> Dict:
        """OpenAI analysis (requires API key)"""
        import openai
        openai.api_key = self.openai_api_key

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

        key_sentences = self._extract_key_sentences(sentences, 4)

        analysis_templates = {
            'general': f"""
📊 General Analysis

🔑 Key Terms Identified:
{', '.join(keywords[:10])}

📋 Main Points:
{key_sentences}

💡 This analysis uses smart extraction. For AI-powered deep analysis, add a Groq API key.
            """,
            'methodology': f"""
📊 Methodology Analysis

🔬 Identified Keywords:
{', '.join([k for k in keywords if k in ['method', 'approach', 'model', 'algorithm', 'technique', 'system', 'framework']][:5] or keywords[:5])}

📝 Key Methodological Points:
{key_sentences}

💡 For detailed methodology analysis, consider adding a Groq API key.
            """,
            'findings': f"""
📊 Findings Analysis

🔍 Key Result Terms:
{', '.join([k for k in keywords if k in ['result', 'performance', 'achieve', 'improve', 'show', 'demonstrate']][:5] or keywords[:5])}

📈 Main Findings:
{key_sentences}

💡 For in-depth findings analysis, consider adding a Groq API key.
            """,
            'implications': f"""
📊 Implications Analysis

🎯 Key Concept Terms:
{', '.join(keywords[:8])}

💭 Potential Implications:
{key_sentences}

💡 For detailed implications analysis, consider adding a Groq API key.
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

        scored = []
        for i, sentence in enumerate(sentences):
            score = 1.0 / (i + 1)
            if len(sentence) > 30:
                score += 0.5
            scored.append((sentence, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        return '\n'.join([f"• {s[0]}" for s in scored[:count]])

    def extract_keywords(self, text: str, num_keywords: int = 10) -> list:
        """Extract keywords from text"""
        words = text.lower().split()

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

        keywords = []
        for word in words:
            word = ''.join(c for c in word if c.isalnum())
            if word and word not in stop_words and len(word) > 3:
                keywords.append(word)

        word_count = {}
        for word in keywords:
            word_count[word] = word_count.get(word, 0) + 1

        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)

        return [word for word, count in sorted_words[:num_keywords]]
