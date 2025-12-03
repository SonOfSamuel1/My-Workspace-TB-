#!/usr/bin/env python3
"""
Content Converter - Converts OneNote HTML content to Obsidian Markdown.

This module handles the conversion of OneNote's HTML format to
Obsidian-compatible Markdown, including handling of images,
tables, and special formatting.
"""
import re
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup, NavigableString, Tag
from dataclasses import dataclass, field


@dataclass
class ImageReference:
    """Represents an image that needs to be downloaded."""
    original_url: str
    local_filename: str
    alt_text: str = ""


@dataclass
class ConversionResult:
    """Result of converting a page."""
    markdown: str
    title: str
    images: List[ImageReference] = field(default_factory=list)
    attachments: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContentConverter:
    """Converts OneNote HTML content to Obsidian Markdown."""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize content converter.

        Args:
            config: Optional configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or {}

        # Image handling configuration
        self.image_folder = self.config.get('image_folder', 'attachments')
        self.download_images = self.config.get('download_images', True)

        # Conversion options
        self.include_metadata = self.config.get('include_metadata', True)
        self.preserve_timestamps = self.config.get('preserve_timestamps', True)

    def convert_page(
        self,
        html_content: str,
        page_metadata: Optional[Dict] = None
    ) -> ConversionResult:
        """
        Convert OneNote page HTML to Obsidian Markdown.

        Args:
            html_content: HTML content from OneNote
            page_metadata: Optional page metadata (title, created date, etc.)

        Returns:
            ConversionResult with markdown and resources
        """
        if not html_content:
            return ConversionResult(markdown="", title="Untitled")

        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract title
        title = self._extract_title(soup, page_metadata)

        # Process images and collect references
        images = self._process_images(soup)

        # Process attachments
        attachments = self._process_attachments(soup)

        # Convert HTML to Markdown
        markdown_content = self._html_to_markdown(soup)

        # Add frontmatter if configured
        if self.include_metadata and page_metadata:
            frontmatter = self._generate_frontmatter(page_metadata)
            markdown_content = frontmatter + markdown_content

        return ConversionResult(
            markdown=markdown_content,
            title=title,
            images=images,
            attachments=attachments,
            metadata=page_metadata or {}
        )

    def _extract_title(
        self,
        soup: BeautifulSoup,
        metadata: Optional[Dict]
    ) -> str:
        """Extract page title from HTML or metadata."""
        # Try metadata first
        if metadata and metadata.get('title'):
            return self._sanitize_filename(metadata['title'])

        # Try HTML title tag
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            return self._sanitize_filename(title_tag.string.strip())

        # Try first h1
        h1 = soup.find('h1')
        if h1:
            return self._sanitize_filename(h1.get_text(strip=True))

        # Try data-absolute-enabled attribute (OneNote specific)
        title_div = soup.find('div', {'data-id': True})
        if title_div:
            first_text = title_div.get_text(strip=True)[:50]
            if first_text:
                return self._sanitize_filename(first_text)

        return "Untitled"

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string to be used as a filename."""
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()

        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100].strip()

        return sanitized or "Untitled"

    def _process_images(self, soup: BeautifulSoup) -> List[ImageReference]:
        """
        Process images in the HTML and prepare for download.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of image references
        """
        images = []
        img_count = 0

        for img in soup.find_all('img'):
            src = img.get('src', '') or img.get('data-src', '')

            if not src:
                continue

            img_count += 1
            alt_text = img.get('alt', '') or f'image-{img_count}'

            # Generate a unique filename based on URL hash
            url_hash = hashlib.md5(src.encode()).hexdigest()[:8]
            extension = self._get_image_extension(src)
            filename = f"image-{img_count}-{url_hash}{extension}"

            images.append(ImageReference(
                original_url=src,
                local_filename=filename,
                alt_text=alt_text
            ))

            # Replace img tag with Obsidian image syntax
            if self.download_images:
                obsidian_link = f"![[{self.image_folder}/{filename}]]"
            else:
                obsidian_link = f"![{alt_text}]({src})"

            img.replace_with(obsidian_link)

        return images

    def _get_image_extension(self, url: str) -> str:
        """Determine image extension from URL or default to .png."""
        url_lower = url.lower()

        if '.jpg' in url_lower or '.jpeg' in url_lower:
            return '.jpg'
        elif '.gif' in url_lower:
            return '.gif'
        elif '.svg' in url_lower:
            return '.svg'
        elif '.webp' in url_lower:
            return '.webp'
        elif '.bmp' in url_lower:
            return '.bmp'

        return '.png'

    def _process_attachments(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Process file attachments in the HTML.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of attachment dictionaries
        """
        attachments = []

        # Look for object tags (common for attachments in OneNote)
        for obj in soup.find_all('object'):
            data_url = obj.get('data', '')
            data_type = obj.get('type', '')

            if data_url:
                filename = self._extract_filename_from_url(data_url)
                attachments.append({
                    'url': data_url,
                    'filename': filename,
                    'type': data_type
                })

                # Replace with link
                obj.replace_with(f"[[{self.image_folder}/{filename}]]")

        # Look for file attachment links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')

            if 'onenote://' in href or 'file:' in href.lower():
                filename = link.get_text(strip=True) or self._extract_filename_from_url(href)
                attachments.append({
                    'url': href,
                    'filename': filename,
                    'type': 'link'
                })

        return attachments

    def _extract_filename_from_url(self, url: str) -> str:
        """Extract filename from URL."""
        # Remove query parameters
        url = url.split('?')[0]

        # Get last path component
        parts = url.rstrip('/').split('/')
        filename = parts[-1] if parts else 'attachment'

        return self._sanitize_filename(filename)

    def _html_to_markdown(self, soup: BeautifulSoup) -> str:
        """
        Convert HTML body to Markdown.

        Args:
            soup: BeautifulSoup object

        Returns:
            Markdown string
        """
        # Find the body content
        body = soup.find('body') or soup

        # Remove script and style tags
        for tag in body.find_all(['script', 'style', 'meta', 'link']):
            tag.decompose()

        # Convert the HTML to Markdown
        markdown_lines = []
        self._process_element(body, markdown_lines)

        # Clean up the result
        markdown = '\n'.join(markdown_lines)
        markdown = self._clean_markdown(markdown)

        return markdown

    def _process_element(
        self,
        element: Tag,
        lines: List[str],
        indent: int = 0,
        list_type: Optional[str] = None,
        list_index: int = 0
    ):
        """
        Recursively process an HTML element and convert to Markdown.

        Args:
            element: BeautifulSoup element
            lines: List to append markdown lines to
            indent: Current indentation level
            list_type: Current list type ('ul', 'ol', or None)
            list_index: Current list item index
        """
        if isinstance(element, NavigableString):
            text = str(element)
            if text.strip():
                lines.append(text)
            return

        if not isinstance(element, Tag):
            return

        tag_name = element.name.lower()

        # Handle different tag types
        if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(tag_name[1])
            text = element.get_text(strip=True)
            if text:
                lines.append('')
                lines.append('#' * level + ' ' + text)
                lines.append('')

        elif tag_name == 'p':
            text = self._process_inline_elements(element)
            if text.strip():
                lines.append('')
                lines.append(text)
                lines.append('')

        elif tag_name == 'br':
            lines.append('')

        elif tag_name == 'hr':
            lines.append('')
            lines.append('---')
            lines.append('')

        elif tag_name == 'ul':
            lines.append('')
            for i, child in enumerate(element.children):
                if isinstance(child, Tag) and child.name == 'li':
                    self._process_list_item(child, lines, indent, 'ul', i + 1)
            lines.append('')

        elif tag_name == 'ol':
            lines.append('')
            for i, child in enumerate(element.children):
                if isinstance(child, Tag) and child.name == 'li':
                    self._process_list_item(child, lines, indent, 'ol', i + 1)
            lines.append('')

        elif tag_name == 'li':
            self._process_list_item(element, lines, indent, list_type, list_index)

        elif tag_name == 'blockquote':
            text = self._process_inline_elements(element)
            for line in text.split('\n'):
                lines.append('> ' + line)

        elif tag_name == 'pre':
            code = element.get_text()
            lines.append('')
            lines.append('```')
            lines.append(code)
            lines.append('```')
            lines.append('')

        elif tag_name == 'code':
            text = element.get_text()
            lines.append(f'`{text}`')

        elif tag_name == 'table':
            self._process_table(element, lines)

        elif tag_name == 'div':
            # Process children
            for child in element.children:
                self._process_element(child, lines, indent)

        elif tag_name == 'span':
            text = self._process_inline_elements(element)
            if text.strip():
                lines.append(text)

        elif tag_name in ['strong', 'b']:
            text = element.get_text()
            lines.append(f'**{text}**')

        elif tag_name in ['em', 'i']:
            text = element.get_text()
            lines.append(f'*{text}*')

        elif tag_name == 'a':
            href = element.get('href', '')
            text = element.get_text(strip=True)

            if href and text:
                # Check if it's an internal OneNote link
                if 'onenote://' in href:
                    # Convert to wiki link
                    lines.append(f'[[{text}]]')
                else:
                    lines.append(f'[{text}]({href})')
            elif text:
                lines.append(text)

        elif tag_name in ['img', 'object']:
            # These should have been processed earlier
            pass

        else:
            # Default: process children
            for child in element.children:
                self._process_element(child, lines, indent)

    def _process_list_item(
        self,
        element: Tag,
        lines: List[str],
        indent: int,
        list_type: str,
        index: int
    ):
        """Process a list item element."""
        prefix = '  ' * indent

        if list_type == 'ol':
            marker = f'{index}. '
        else:
            marker = '- '

        # Get the text content
        text = self._process_inline_elements(element)

        lines.append(f'{prefix}{marker}{text}')

        # Check for nested lists
        for child in element.children:
            if isinstance(child, Tag) and child.name in ['ul', 'ol']:
                for i, nested in enumerate(child.children):
                    if isinstance(nested, Tag) and nested.name == 'li':
                        self._process_list_item(
                            nested, lines, indent + 1, child.name, i + 1
                        )

    def _process_inline_elements(self, element: Tag) -> str:
        """Process inline elements and return text with formatting."""
        result = []

        for child in element.children:
            if isinstance(child, NavigableString):
                result.append(str(child))
            elif isinstance(child, Tag):
                tag_name = child.name.lower()

                if tag_name in ['strong', 'b']:
                    text = child.get_text()
                    result.append(f'**{text}**')
                elif tag_name in ['em', 'i']:
                    text = child.get_text()
                    result.append(f'*{text}*')
                elif tag_name == 'code':
                    text = child.get_text()
                    result.append(f'`{text}`')
                elif tag_name == 'a':
                    href = child.get('href', '')
                    text = child.get_text(strip=True)
                    if href and text:
                        if 'onenote://' in href:
                            result.append(f'[[{text}]]')
                        else:
                            result.append(f'[{text}]({href})')
                    elif text:
                        result.append(text)
                elif tag_name == 'br':
                    result.append('\n')
                elif tag_name in ['u', 'ins']:
                    text = child.get_text()
                    result.append(f'<u>{text}</u>')
                elif tag_name in ['s', 'del', 'strike']:
                    text = child.get_text()
                    result.append(f'~~{text}~~')
                elif tag_name == 'span':
                    # Recursively process span
                    result.append(self._process_inline_elements(child))
                else:
                    # Default: get text
                    result.append(child.get_text())

        return ''.join(result)

    def _process_table(self, table: Tag, lines: List[str]):
        """Convert HTML table to Markdown table."""
        lines.append('')

        rows = table.find_all('tr')
        if not rows:
            return

        # Process header row
        header_cells = rows[0].find_all(['th', 'td'])
        if header_cells:
            header = '| ' + ' | '.join(
                self._process_inline_elements(cell).strip().replace('|', '\\|')
                for cell in header_cells
            ) + ' |'
            lines.append(header)

            # Separator
            separator = '| ' + ' | '.join(
                '---' for _ in header_cells
            ) + ' |'
            lines.append(separator)

        # Process data rows
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if cells:
                row_text = '| ' + ' | '.join(
                    self._process_inline_elements(cell).strip().replace('|', '\\|')
                    for cell in cells
                ) + ' |'
                lines.append(row_text)

        lines.append('')

    def _generate_frontmatter(self, metadata: Dict[str, Any]) -> str:
        """Generate YAML frontmatter for the markdown file."""
        frontmatter_lines = ['---']

        if metadata.get('title'):
            title = metadata['title'].replace('"', '\\"')
            frontmatter_lines.append(f'title: "{title}"')

        if self.preserve_timestamps:
            if metadata.get('createdDateTime'):
                frontmatter_lines.append(f"created: {metadata['createdDateTime']}")

            if metadata.get('lastModifiedDateTime'):
                frontmatter_lines.append(f"modified: {metadata['lastModifiedDateTime']}")

        # Add source information
        frontmatter_lines.append('source: OneNote')

        if metadata.get('id'):
            frontmatter_lines.append(f"onenote_id: {metadata['id']}")

        frontmatter_lines.append('---')
        frontmatter_lines.append('')

        return '\n'.join(frontmatter_lines)

    def _clean_markdown(self, markdown: str) -> str:
        """Clean up the generated markdown."""
        # Remove excessive blank lines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)

        # Remove leading/trailing whitespace on lines
        lines = [line.rstrip() for line in markdown.split('\n')]
        markdown = '\n'.join(lines)

        # Ensure single newline at end
        markdown = markdown.strip() + '\n'

        return markdown
