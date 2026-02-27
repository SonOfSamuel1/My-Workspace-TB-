#!/usr/bin/env python3
"""
Reflection Question Generator

Uses Claude Haiku to generate 2 personal reflection questions per teaching.
Supports both native Anthropic API and OpenRouter (with Bedrock/Vertex fallback).
"""

import logging
import os
import re
from typing import List

logger = logging.getLogger(__name__)

# Model IDs
MODEL_NATIVE = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
MODEL_OPENROUTER = os.getenv("CLAUDE_MODEL", "anthropic/claude-3-5-haiku")

PROMPT_TEMPLATE = """Teaching: {title}

Key Verse: {verse}

Key Insights:
{core_content}

Generate exactly 2 short, personal reflection questions that help someone apply this teaching today. The questions should be specific, actionable, and invite honest self-examination. Return only the 2 questions, numbered 1. and 2."""  # noqa: E501


class QuestionGenerator:
    """Generates reflection questions for teachings via Claude API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = os.getenv("ANTHROPIC_BASE_URL")
        self.use_openrouter = bool(self.base_url)

        if self.use_openrouter:
            logger.info(f"Using OpenRouter: {self.base_url}")
        else:
            import anthropic

            self.client = anthropic.Anthropic(api_key=api_key)

    def generate_questions(self, teaching: dict) -> List[str]:
        """
        Generate 2 reflection questions for a teaching.

        Args:
            teaching: Dict with keys: title, verse, core_content

        Returns:
            List of 2 question strings
        """
        title = teaching.get("title", "Unknown Teaching")
        verse = teaching.get("verse", "").strip() or "(No verse found)"
        core_content = (
            teaching.get("core_content", "").strip() or "(See teaching content)"
        )

        prompt = PROMPT_TEMPLATE.format(
            title=title,
            verse=verse[:500],
            core_content=core_content,
        )

        logger.info(f"Generating reflection questions for: {title}")

        try:
            if self.use_openrouter:
                response_text = self._call_openrouter(prompt)
            else:
                response_text = self._call_anthropic(prompt)

            questions = self._parse_questions(response_text)

            if len(questions) == 2:
                logger.info(f"Generated 2 questions for '{title}'")
                return questions
            else:
                logger.warning(
                    f"Expected 2 questions, got {len(questions)}. Using fallback."
                )
                return self._fallback_questions(title, questions)

        except Exception as e:
            logger.error(f"Error generating questions for '{title}': {e}")
            return self._fallback_questions(title, [])

    def _call_anthropic(self, prompt: str) -> str:
        """Call native Anthropic API."""
        message = self.client.messages.create(
            model=MODEL_NATIVE,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()

    def _call_openrouter(self, prompt: str) -> str:
        """Call OpenRouter API directly via HTTP (supports provider routing)."""
        import json
        import urllib.request

        # Strip trailing /v1 if present — we add it ourselves
        base = self.base_url.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]

        url = f"{base}/v1/chat/completions"

        payload = {
            "model": MODEL_OPENROUTER,
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}],
            "provider": {
                "allow_fallbacks": True,
                "order": ["Amazon Bedrock", "Google Vertex AI"],
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/SonOfSamuel1/My-Workspace-TB-",
                "X-Title": "JT Teaching Newsletter",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        return data["choices"][0]["message"]["content"].strip()

    def _parse_questions(self, text: str) -> List[str]:
        """Parse numbered questions from Claude response."""
        pattern = r"^\s*[12][.)]\s+(.+?)(?=\s*[12][.)]|\Z)"
        matches = re.findall(pattern, text, re.DOTALL | re.MULTILINE)

        if matches:
            return [q.strip() for q in matches if q.strip()]

        lines = [
            line_item.strip() for line_item in text.split("\n") if line_item.strip()
        ]
        questions = []
        for line in lines:
            if re.match(r"^[12][.)]", line):
                q = re.sub(r"^[12][.)]\s*", "", line).strip()
                if q:
                    questions.append(q)

        return questions

    def _fallback_questions(self, title: str, partial: List[str]) -> List[str]:
        """Return generic fallback questions if generation fails."""
        defaults = [
            f"How does the teaching on '{title}' apply to a specific situation in your life today?",
            "What one action could you take today to put this teaching into practice?",
        ]
        result = list(partial[:2])
        while len(result) < 2:
            result.append(defaults[len(result)])
        return result[:2]
