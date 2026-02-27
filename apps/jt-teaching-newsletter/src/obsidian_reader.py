#!/usr/bin/env python3
"""
Obsidian Note Reader

Reads JT- teaching notes from S3 and extracts structured content:
- Title (from filename)
- Key verse(s)
- Core content for context
"""

import logging
import re
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ObsidianReader:
    """Parse JT- Obsidian teaching notes from S3."""

    def __init__(self, bucket: str, region: str = "us-east-1", vault_path: str = None):
        self.bucket = bucket
        self.s3 = boto3.client("s3", region_name=region)
        # Derive Book Study path from vault path (sibling directory)
        self._book_study_path = None
        if vault_path:
            vault_dir = Path(vault_path).parent  # parent of "Permanent Notes"
            candidate = vault_dir / "Book Study"
            if candidate.exists():
                self._book_study_path = str(candidate)
                logger.info(f"Book Study path: {self._book_study_path}")
            else:
                logger.debug(f"Book Study directory not found at: {candidate}")

    def read_teaching(self, s3_key: str) -> dict:
        """
        Read and parse a teaching .md file from S3.

        Args:
            s3_key: S3 object key (e.g. 'JT- Be Merciful.md')

        Returns:
            Dict with keys: title, verse, core_content, raw
        """
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=s3_key)
            raw = response["Body"].read().decode("utf-8")
        except ClientError as e:
            logger.error(f"Failed to read {s3_key} from S3: {e}")
            raise

        title = self._extract_title(s3_key)
        verse = self._extract_verse(raw)
        if not verse and self._book_study_path:
            verse = self._find_verse_from_vault_backlinks(title, self._book_study_path)
        # If verse is just a reference with no body text, fetch the actual verse
        verse = self._resolve_verse_body(verse)
        core_content = self._extract_core_content(raw)

        return {
            "title": title,
            "verse": verse,
            "core_content": core_content,
            "raw": raw,
            "s3_key": s3_key,
        }

    def _extract_title(self, s3_key: str) -> str:
        """Extract human-readable title from filename."""
        # Remove path prefix if any
        filename = s3_key.split("/")[-1]
        # Strip extension
        name = filename.replace(".md", "")
        # Strip 'JT- ' prefix
        if name.startswith("JT- "):
            name = name[4:]
        elif name.startswith("JT-"):
            name = name[3:]
        return name.strip()

    def _first_verse_block(self, text: str) -> str:
        """
        Within a multi-verse block, find the first Bible reference line and
        return from it until the next reference line or double-blank-line.
        Falls back to the full text if no reference line found.
        """
        ref_pattern = re.compile(
            r"^(?:\d\s+)?[A-Z]\w+(?:\s+\w+)?\s+\d+[:\d\u2013\-,\s]*(?:\([^)]+\))?",
            re.MULTILINE,
        )
        match = ref_pattern.search(text)
        if not match:
            return text  # no reference found, use all
        start = match.start()
        next_match = ref_pattern.search(text, match.end() + 1)
        end = next_match.start() if next_match else len(text)
        return text[start:end].strip()

    def _extract_verse(self, content: str) -> str:
        """
        Extract key verse text from the note.

        Priority:
          1. # or ## Key Verses / Key Scriptures / Scripture / Verse heading
          2. Bible reference line near top of file (no heading)
          3. Blockquote fallback
        """
        # 1. Heading-based patterns — match both h1 (#) and h2 (##)
        patterns = [
            r"#{1,2}\s+Key Verses?\s*\n(.*?)(?=\n#{1,2}\s|\Z)",
            r"#{1,2}\s+Key Scriptures?\s*\n(.*?)(?=\n#{1,2}\s|\Z)",
            r"#{1,2}\s+Scripture\s*\n(.*?)(?=\n#{1,2}\s|\Z)",
            r"#{1,2}\s+Verse\s*\n(.*?)(?=\n#{1,2}\s|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                verse_text = self._first_verse_block(match.group(1).strip())
                verse_text = self._clean_obsidian_syntax(verse_text)
                if verse_text:
                    return verse_text

        # 2. Bible reference line at top of file (no heading)
        ref_line_pattern = re.compile(
            r"^(?:\d\s+)?[A-Z]\w+(?:\s+\w+)?\s+\d+[:\d\u2013\-,\s]*(?:\([^)]+\))?"
        )
        lines = content.strip().splitlines()
        for i, line in enumerate(lines[:100]):
            stripped = line.strip()
            # Skip front-matter blocks, wikilinks, tags, property lines
            if (
                stripped.startswith("---")
                or stripped.startswith("[[")
                or stripped.startswith("#")
                or re.match(r"^\w[\w\s]*:\s", stripped)
            ):
                continue
            if ref_line_pattern.match(stripped):
                verse_text = "\n".join(lines[i:])
                verse_text = re.split(r"\n#{1,2}\s", verse_text)[0]
                verse_text = self._clean_obsidian_syntax(verse_text).strip()
                if verse_text:
                    return verse_text

        # 3. Fallback: look for any blockquote at the start of content
        blockquote_match = re.search(
            r"^>\s+(.+?)(?=\n[^>]|\Z)", content, re.MULTILINE | re.DOTALL
        )
        if blockquote_match:
            verse_text = blockquote_match.group(0).strip()
            # Clean blockquote markers
            verse_text = re.sub(r"^>\s?", "", verse_text, flags=re.MULTILINE)
            return self._clean_obsidian_syntax(verse_text).strip()

        return ""

    def _find_verse_from_vault_backlinks(self, title: str, book_study_path: str) -> str:
        """
        Search Book Study files for [[JT- {title}]] and extract the verse
        text that appears above the wikilink in that file.
        """
        book_study_dir = Path(book_study_path)
        if not book_study_dir.exists():
            logger.warning(f"Book Study path not found: {book_study_path}")
            return ""

        search_terms = [
            f"[[JT- {title}]]",
            f"[[{title}]]",
        ]
        ref_pattern = re.compile(
            r"^(?:\d\s+)?[A-Z]\w+(?:\s+\w+)?\s+\d+[:\d\u2013\-,\s]*(?:\([^)]+\))?"
        )

        for md_file in book_study_dir.glob("*.md"):
            try:
                text = md_file.read_text(encoding="utf-8")
            except Exception:
                continue
            for term in search_terms:
                idx = text.find(term)
                if idx == -1:
                    continue
                # Search backwards from the wikilink for the nearest verse reference line
                before = text[:idx]
                lines_before = before.splitlines()
                verse_lines = []
                for line in reversed(lines_before):
                    stripped = line.strip()
                    if ref_pattern.match(stripped):
                        verse_lines.insert(0, stripped)
                        break
                    if (
                        stripped
                        and not stripped.startswith("-")
                        and not stripped.startswith("#")
                    ):
                        verse_lines.insert(0, stripped)
                    elif not stripped:
                        if verse_lines:
                            break  # stop at blank line after content starts
                if verse_lines:
                    result = "\n".join(verse_lines).strip()
                    logger.info(f"Found verse via backlink in {md_file.name}")
                    return self._clean_obsidian_syntax(result)
        return ""

    def _resolve_verse_body(self, verse: str) -> str:
        """If verse is only a reference with no body text, fetch the body from Bible API."""
        if not verse:
            return verse

        non_empty = [
            line_item for line_item in verse.strip().splitlines() if line_item.strip()
        ]
        if len(non_empty) > 1:
            return verse  # Already has body text

        # Single non-empty line — check if it matches a Bible reference pattern
        ref_pattern = re.compile(
            r"^(?:\d\s+)?[A-Z]\w+(?:\s+\w+)?\s+\d+[:\d\u2013\-,\s]*(?:\([^)]+\))?$"
        )
        if not ref_pattern.match(verse.strip()):
            return verse

        body = self._fetch_verse_text(verse.strip())
        if body:
            return f'{verse.strip()}\n"{body}"'
        return verse

    def _fetch_verse_text(self, reference: str) -> str:
        """Fetch verse text from bible-api.com given a reference like 'Matthew 5:44 (ESV)'."""
        import json
        import urllib.request

        # Strip translation in parentheses: "Matthew 5:44 (ESV)" → "Matthew 5:44"
        ref = re.sub(r"\s*\([^)]+\)\s*$", "", reference.strip())
        query = ref.replace(" ", "+")
        url = f"https://bible-api.com/{query}"

        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "JT-Newsletter/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            text = data.get("text", "").strip()
            # Collapse whitespace for clean single-paragraph display
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                logger.info(f"Fetched verse text for '{reference}': {text[:80]}...")
                return text
        except Exception as e:
            logger.warning(f"Could not fetch verse text for '{reference}': {e}")

        return ""

    def _extract_core_content(self, content: str) -> str:
        """
        Extract key insights from teaching sections.

        Looks for: ## Understandings, ## How, ## Applications,
                   ## Summary, ## Overview, ## Teaching, ## Key Points
        Returns combined text (truncated to ~800 chars for Claude prompt).
        """
        heading_patterns = [
            r"##\s+Understandings?\s*\n(.*?)(?=\n##|\Z)",
            r"##\s+How\s*\n(.*?)(?=\n##|\Z)",
            r"##\s+Applications?\s*\n(.*?)(?=\n##|\Z)",
            r"##\s+Summary\s*\n(.*?)(?=\n##|\Z)",
            r"##\s+Overview\s*\n(.*?)(?=\n##|\Z)",
            r"##\s+Teaching\s*\n(.*?)(?=\n##|\Z)",
            r"##\s+Key Points?\s*\n(.*?)(?=\n##|\Z)",
            r"##\s+Notes?\s*\n(.*?)(?=\n##|\Z)",
        ]

        parts = []
        for pattern in heading_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                section = match.group(1).strip()
                section = self._clean_obsidian_syntax(section)
                if section:
                    parts.append(section)

        if not parts:
            # Fallback: grab body after front matter / first heading
            body = re.sub(r"^---.*?---\s*", "", content, flags=re.DOTALL)
            body = re.sub(r"^#.*?\n", "", body)
            body = self._clean_obsidian_syntax(body).strip()
            parts.append(body)

        combined = "\n\n".join(parts)
        # Trim to 800 chars to keep Claude prompt concise
        if len(combined) > 800:
            combined = combined[:797] + "..."
        return combined

    def _clean_obsidian_syntax(self, text: str) -> str:
        """Remove Obsidian-specific syntax from text."""
        # Remove image embeds: ![[...]]
        text = re.sub(r"!\[\[.*?\]\]", "", text)
        # Convert wiki links [[Target|Display]] → Display, [[Target]] → Target
        text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
        text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
        # Remove highlights ==text==
        text = re.sub(r"==(.+?)==", r"\1", text)
        # Remove bold/italic markers
        text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        # Remove markdown checkboxes
        text = re.sub(r"- \[[ xX]\] ", "- ", text)
        # Remove tags
        text = re.sub(r"#\w+", "", text)
        # Clean up multiple blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def list_teachings(self, prefix: str = "JT-") -> list:
        """List all JT- teaching files in S3 bucket."""
        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix)

            keys = []
            for page in pages:
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key.endswith(".md"):
                        keys.append(key)

            logger.info(f"Found {len(keys)} JT- teaching files in S3")
            return sorted(keys)

        except ClientError as e:
            logger.error(f"Failed to list S3 objects: {e}")
            raise
