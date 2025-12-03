#!/usr/bin/env python3
"""
Obsidian Writer - Writes converted content to an Obsidian vault.

This module handles creating the folder structure and writing
markdown files and attachments to an Obsidian vault.
"""
import os
import re
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from content_converter import ConversionResult, ImageReference


@dataclass
class MigrationStats:
    """Statistics for the migration process."""
    notebooks_processed: int = 0
    sections_processed: int = 0
    pages_processed: int = 0
    pages_succeeded: int = 0
    pages_failed: int = 0
    images_downloaded: int = 0
    images_failed: int = 0
    attachments_processed: int = 0
    errors: List[str] = field(default_factory=list)


class ObsidianWriter:
    """Writes converted OneNote content to Obsidian vault."""

    def __init__(
        self,
        vault_path: str,
        onenote_service,
        config: Optional[Dict] = None
    ):
        """
        Initialize Obsidian writer.

        Args:
            vault_path: Path to the Obsidian vault
            onenote_service: OneNote service instance for downloading resources
            config: Optional configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.vault_path = Path(vault_path)
        self.onenote_service = onenote_service
        self.config = config or {}

        # Configuration options
        self.attachments_folder = self.config.get('attachments_folder', 'attachments')
        self.create_index_files = self.config.get('create_index_files', True)
        self.preserve_timestamps = self.config.get('preserve_timestamps', True)
        self.skip_existing = self.config.get('skip_existing', False)
        self.dry_run = self.config.get('dry_run', False)

        # Stats tracking
        self.stats = MigrationStats()

    def initialize_vault(self) -> bool:
        """
        Initialize the Obsidian vault directory.

        Returns:
            True if successful
        """
        try:
            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would create vault at: {self.vault_path}")
                return True

            self.vault_path.mkdir(parents=True, exist_ok=True)

            # Create .obsidian folder if it doesn't exist
            obsidian_config = self.vault_path / '.obsidian'
            obsidian_config.mkdir(exist_ok=True)

            # Create attachments folder
            attachments_path = self.vault_path / self.attachments_folder
            attachments_path.mkdir(exist_ok=True)

            self.logger.info(f"Initialized vault at: {self.vault_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize vault: {e}")
            return False

    def write_notebook(
        self,
        notebook: Dict[str, Any],
        converter
    ) -> bool:
        """
        Write a complete notebook to the vault.

        Args:
            notebook: Notebook data with sections and pages
            converter: ContentConverter instance

        Returns:
            True if successful
        """
        notebook_name = self._sanitize_path(notebook.get('displayName', 'Untitled Notebook'))
        notebook_path = self.vault_path / notebook_name

        try:
            if not self.dry_run:
                notebook_path.mkdir(parents=True, exist_ok=True)

            self.logger.info(f"Processing notebook: {notebook_name}")
            self.stats.notebooks_processed += 1

            # Process sections
            for section in notebook.get('sections', []):
                self.write_section(section, notebook_path, converter)

            # Process section groups (nested folders)
            for group in notebook.get('sectionGroups', []):
                self.write_section_group(group, notebook_path, converter)

            # Create notebook index file
            if self.create_index_files:
                self._create_notebook_index(notebook, notebook_path)

            return True

        except Exception as e:
            self.logger.error(f"Failed to write notebook {notebook_name}: {e}")
            self.stats.errors.append(f"Notebook {notebook_name}: {str(e)}")
            return False

    def write_section_group(
        self,
        group: Dict[str, Any],
        parent_path: Path,
        converter
    ):
        """
        Write a section group (folder) to the vault.

        Args:
            group: Section group data
            parent_path: Parent folder path
            converter: ContentConverter instance
        """
        group_name = self._sanitize_path(group.get('displayName', 'Untitled Group'))
        group_path = parent_path / group_name

        try:
            if not self.dry_run:
                group_path.mkdir(parents=True, exist_ok=True)

            self.logger.info(f"Processing section group: {group_name}")

            # Process sections in this group
            for section in group.get('sections', []):
                self.write_section(section, group_path, converter)

            # Process nested section groups
            for nested_group in group.get('sectionGroups', []):
                self.write_section_group(nested_group, group_path, converter)

        except Exception as e:
            self.logger.error(f"Failed to write section group {group_name}: {e}")
            self.stats.errors.append(f"Section group {group_name}: {str(e)}")

    def write_section(
        self,
        section: Dict[str, Any],
        parent_path: Path,
        converter
    ):
        """
        Write a section (folder with pages) to the vault.

        Args:
            section: Section data with pages
            parent_path: Parent folder path
            converter: ContentConverter instance
        """
        section_name = self._sanitize_path(section.get('displayName', 'Untitled Section'))
        section_path = parent_path / section_name

        try:
            if not self.dry_run:
                section_path.mkdir(parents=True, exist_ok=True)

            self.logger.info(f"Processing section: {section_name}")
            self.stats.sections_processed += 1

            # Process pages
            pages = section.get('pages', [])
            for page in pages:
                self.write_page(page, section_path, converter)

            # Create section index file
            if self.create_index_files:
                self._create_section_index(section, section_path)

        except Exception as e:
            self.logger.error(f"Failed to write section {section_name}: {e}")
            self.stats.errors.append(f"Section {section_name}: {str(e)}")

    def write_page(
        self,
        page: Dict[str, Any],
        section_path: Path,
        converter
    ) -> bool:
        """
        Write a single page to the vault.

        Args:
            page: Page metadata
            section_path: Section folder path
            converter: ContentConverter instance

        Returns:
            True if successful
        """
        page_title = self._sanitize_path(page.get('title', 'Untitled'))
        page_id = page.get('id')

        self.stats.pages_processed += 1

        try:
            # Check if page already exists
            page_file = section_path / f"{page_title}.md"

            if self.skip_existing and page_file.exists():
                self.logger.info(f"Skipping existing page: {page_title}")
                self.stats.pages_succeeded += 1
                return True

            # Get page content from OneNote
            self.logger.info(f"Fetching content for page: {page_title}")
            html_content = self.onenote_service.get_page_content(page_id)

            if not html_content:
                self.logger.warning(f"No content for page: {page_title}")
                self.stats.pages_failed += 1
                return False

            # Convert to Markdown
            result = converter.convert_page(html_content, page)

            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would write page: {page_file}")
                self.stats.pages_succeeded += 1
                return True

            # Download images
            self._download_images(result.images, section_path)

            # Write markdown file
            with open(page_file, 'w', encoding='utf-8') as f:
                f.write(result.markdown)

            # Set file timestamps if preserving
            if self.preserve_timestamps and page.get('lastModifiedDateTime'):
                self._set_file_timestamp(page_file, page)

            self.logger.info(f"Wrote page: {page_title}")
            self.stats.pages_succeeded += 1
            return True

        except Exception as e:
            self.logger.error(f"Failed to write page {page_title}: {e}")
            self.stats.pages_failed += 1
            self.stats.errors.append(f"Page {page_title}: {str(e)}")
            return False

    def _download_images(
        self,
        images: List[ImageReference],
        page_path: Path
    ):
        """
        Download images and save to attachments folder.

        Args:
            images: List of image references
            page_path: Path to the page folder
        """
        if not images:
            return

        # Use vault-level attachments folder
        attachments_path = self.vault_path / self.attachments_folder
        attachments_path.mkdir(exist_ok=True)

        for img in images:
            try:
                target_path = attachments_path / img.local_filename

                if target_path.exists() and self.skip_existing:
                    self.logger.debug(f"Skipping existing image: {img.local_filename}")
                    continue

                if self.dry_run:
                    self.logger.info(f"[DRY RUN] Would download: {img.local_filename}")
                    continue

                # Download the image
                content = self.onenote_service.download_resource(img.original_url)

                if content:
                    with open(target_path, 'wb') as f:
                        f.write(content)

                    self.logger.debug(f"Downloaded image: {img.local_filename}")
                    self.stats.images_downloaded += 1
                else:
                    self.logger.warning(f"Failed to download image: {img.original_url}")
                    self.stats.images_failed += 1

            except Exception as e:
                self.logger.error(f"Error downloading image {img.local_filename}: {e}")
                self.stats.images_failed += 1

    def _sanitize_path(self, name: str) -> str:
        """Sanitize a string to be used as a folder/file name."""
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()

        # Handle special cases
        sanitized = sanitized.strip('.')

        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100].strip()

        return sanitized or "Untitled"

    def _set_file_timestamp(self, file_path: Path, page: Dict[str, Any]):
        """Set file modification timestamp from page metadata."""
        try:
            from dateutil import parser

            modified = page.get('lastModifiedDateTime')
            if modified:
                dt = parser.parse(modified)
                timestamp = dt.timestamp()
                os.utime(file_path, (timestamp, timestamp))

        except Exception as e:
            self.logger.debug(f"Could not set timestamp: {e}")

    def _create_notebook_index(self, notebook: Dict[str, Any], notebook_path: Path):
        """Create an index file for the notebook."""
        if self.dry_run:
            return

        index_path = notebook_path / f"{notebook_path.name}.md"

        content = [
            '---',
            f'title: "{notebook.get("displayName", "Notebook")}"',
            'type: notebook-index',
            f'created: {notebook.get("createdDateTime", "")}',
            '---',
            '',
            f'# {notebook.get("displayName", "Notebook")}',
            '',
            '## Sections',
            ''
        ]

        # List sections
        for section in notebook.get('sections', []):
            section_name = section.get('displayName', 'Untitled')
            content.append(f'- [[{section_name}/{section_name}|{section_name}]]')

        # List section groups
        if notebook.get('sectionGroups'):
            content.append('')
            content.append('## Section Groups')
            content.append('')

            for group in notebook['sectionGroups']:
                group_name = group.get('displayName', 'Untitled')
                content.append(f'- [[{group_name}|{group_name}]]')

        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
        except Exception as e:
            self.logger.debug(f"Could not create notebook index: {e}")

    def _create_section_index(self, section: Dict[str, Any], section_path: Path):
        """Create an index file for the section."""
        if self.dry_run:
            return

        index_path = section_path / f"{section_path.name}.md"

        content = [
            '---',
            f'title: "{section.get("displayName", "Section")}"',
            'type: section-index',
            '---',
            '',
            f'# {section.get("displayName", "Section")}',
            '',
            '## Pages',
            ''
        ]

        # List pages
        for page in section.get('pages', []):
            page_title = self._sanitize_path(page.get('title', 'Untitled'))
            content.append(f'- [[{page_title}]]')

        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
        except Exception as e:
            self.logger.debug(f"Could not create section index: {e}")

    def write_migration_log(self):
        """Write migration statistics to a log file."""
        if self.dry_run:
            return

        log_path = self.vault_path / '_migration_log.md'

        content = [
            '---',
            'title: OneNote Migration Log',
            f'date: {datetime.now().isoformat()}',
            '---',
            '',
            '# OneNote to Obsidian Migration Log',
            '',
            '## Statistics',
            '',
            f'- **Notebooks processed:** {self.stats.notebooks_processed}',
            f'- **Sections processed:** {self.stats.sections_processed}',
            f'- **Pages processed:** {self.stats.pages_processed}',
            f'- **Pages succeeded:** {self.stats.pages_succeeded}',
            f'- **Pages failed:** {self.stats.pages_failed}',
            f'- **Images downloaded:** {self.stats.images_downloaded}',
            f'- **Images failed:** {self.stats.images_failed}',
            ''
        ]

        if self.stats.errors:
            content.extend([
                '## Errors',
                ''
            ])
            for error in self.stats.errors:
                content.append(f'- {error}')

        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))

            self.logger.info(f"Migration log written to: {log_path}")

        except Exception as e:
            self.logger.error(f"Failed to write migration log: {e}")

    def get_stats_summary(self) -> str:
        """Get a human-readable summary of migration statistics."""
        lines = [
            '',
            '=' * 60,
            'MIGRATION SUMMARY',
            '=' * 60,
            '',
            f'  Notebooks:     {self.stats.notebooks_processed}',
            f'  Sections:      {self.stats.sections_processed}',
            f'  Pages:         {self.stats.pages_processed}',
            f'    - Succeeded: {self.stats.pages_succeeded}',
            f'    - Failed:    {self.stats.pages_failed}',
            f'  Images:        {self.stats.images_downloaded} downloaded, {self.stats.images_failed} failed',
            ''
        ]

        if self.stats.errors:
            lines.extend([
                f'  Errors:        {len(self.stats.errors)}',
                ''
            ])

        success_rate = (
            self.stats.pages_succeeded / self.stats.pages_processed * 100
            if self.stats.pages_processed > 0 else 0
        )
        lines.append(f'  Success Rate:  {success_rate:.1f}%')
        lines.append('')
        lines.append('=' * 60)

        return '\n'.join(lines)
