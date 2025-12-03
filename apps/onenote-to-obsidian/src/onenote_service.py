#!/usr/bin/env python3
"""
OneNote Service - Microsoft Graph API integration for OneNote access.

This module handles authentication and data extraction from OneNote
using Microsoft Graph API.
"""
import os
import json
import logging
import msal
import requests
from typing import Optional, List, Dict, Any
from pathlib import Path


class OneNoteService:
    """Service for accessing OneNote data via Microsoft Graph API."""

    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tenant_id: Optional[str] = None,
        token_cache_path: Optional[str] = None
    ):
        """
        Initialize OneNote service.

        Args:
            client_id: Azure AD application client ID
            client_secret: Azure AD application client secret (for app-only auth)
            tenant_id: Azure AD tenant ID
            token_cache_path: Path to cache authentication tokens
        """
        self.logger = logging.getLogger(__name__)

        self.client_id = client_id or os.getenv('AZURE_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('AZURE_CLIENT_SECRET')
        self.tenant_id = tenant_id or os.getenv('AZURE_TENANT_ID', 'common')
        self.token_cache_path = token_cache_path or os.getenv(
            'AZURE_TOKEN_CACHE',
            str(Path(__file__).parent.parent / 'credentials' / 'token_cache.json')
        )

        if not self.client_id:
            raise ValueError("Azure Client ID is required. Set AZURE_CLIENT_ID environment variable.")

        self._access_token: Optional[str] = None
        self._msal_app: Optional[msal.PublicClientApplication] = None

        # Scopes needed for OneNote access
        self.scopes = [
            "Notes.Read",
            "Notes.Read.All",
            "User.Read"
        ]

    def _get_token_cache(self) -> msal.SerializableTokenCache:
        """Load or create token cache."""
        cache = msal.SerializableTokenCache()

        if os.path.exists(self.token_cache_path):
            with open(self.token_cache_path, 'r') as f:
                cache.deserialize(f.read())

        return cache

    def _save_token_cache(self, cache: msal.SerializableTokenCache):
        """Save token cache to file."""
        os.makedirs(os.path.dirname(self.token_cache_path), exist_ok=True)

        if cache.has_state_changed:
            with open(self.token_cache_path, 'w') as f:
                f.write(cache.serialize())

    def _get_msal_app(self) -> msal.PublicClientApplication:
        """Get or create MSAL application instance."""
        if self._msal_app is None:
            cache = self._get_token_cache()

            authority = f"https://login.microsoftonline.com/{self.tenant_id}"

            self._msal_app = msal.PublicClientApplication(
                client_id=self.client_id,
                authority=authority,
                token_cache=cache
            )

        return self._msal_app

    def authenticate(self) -> bool:
        """
        Authenticate with Microsoft Graph API using device code flow.

        Returns:
            True if authentication successful
        """
        app = self._get_msal_app()

        # Check for cached token
        accounts = app.get_accounts()
        if accounts:
            self.logger.info(f"Found cached account: {accounts[0]['username']}")
            result = app.acquire_token_silent(self.scopes, account=accounts[0])

            if result and 'access_token' in result:
                self._access_token = result['access_token']
                self._save_token_cache(app.token_cache)
                self.logger.info("Successfully acquired token from cache")
                return True

        # No cached token, use device code flow
        self.logger.info("Starting device code authentication flow...")

        flow = app.initiate_device_flow(scopes=self.scopes)

        if 'user_code' not in flow:
            self.logger.error(f"Failed to create device flow: {flow}")
            return False

        # Display authentication instructions
        print("\n" + "="*60)
        print("MICROSOFT AUTHENTICATION REQUIRED")
        print("="*60)
        print(f"\nTo authenticate, please:")
        print(f"1. Open a web browser and go to: {flow['verification_uri']}")
        print(f"2. Enter this code: {flow['user_code']}")
        print(f"\nWaiting for authentication...")
        print("="*60 + "\n")

        result = app.acquire_token_by_device_flow(flow)

        if 'access_token' in result:
            self._access_token = result['access_token']
            self._save_token_cache(app.token_cache)
            self.logger.info("Successfully authenticated")
            return True

        self.logger.error(f"Authentication failed: {result.get('error_description', 'Unknown error')}")
        return False

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Make authenticated request to Graph API.

        Args:
            endpoint: API endpoint (relative to base URL)
            params: Query parameters
            headers: Additional headers

        Returns:
            JSON response or None on error
        """
        if not self._access_token:
            if not self.authenticate():
                return None

        url = f"{self.GRAPH_API_BASE}{endpoint}"

        req_headers = {
            'Authorization': f'Bearer {self._access_token}',
            'Content-Type': 'application/json'
        }

        if headers:
            req_headers.update(headers)

        try:
            response = requests.get(url, headers=req_headers, params=params, timeout=30)

            if response.status_code == 401:
                # Token expired, re-authenticate
                self.logger.info("Token expired, re-authenticating...")
                self._access_token = None
                if self.authenticate():
                    return self._make_request(endpoint, params, headers)
                return None

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            return None

    def get_notebooks(self) -> List[Dict[str, Any]]:
        """
        Get all notebooks accessible to the user.

        Returns:
            List of notebook objects
        """
        result = self._make_request('/me/onenote/notebooks')

        if result and 'value' in result:
            notebooks = result['value']
            self.logger.info(f"Found {len(notebooks)} notebooks")
            return notebooks

        return []

    def get_sections(self, notebook_id: str) -> List[Dict[str, Any]]:
        """
        Get all sections in a notebook.

        Args:
            notebook_id: ID of the notebook

        Returns:
            List of section objects
        """
        result = self._make_request(f'/me/onenote/notebooks/{notebook_id}/sections')

        if result and 'value' in result:
            sections = result['value']
            self.logger.info(f"Found {len(sections)} sections in notebook")
            return sections

        return []

    def get_section_groups(self, notebook_id: str) -> List[Dict[str, Any]]:
        """
        Get all section groups in a notebook.

        Args:
            notebook_id: ID of the notebook

        Returns:
            List of section group objects
        """
        result = self._make_request(f'/me/onenote/notebooks/{notebook_id}/sectionGroups')

        if result and 'value' in result:
            groups = result['value']
            self.logger.info(f"Found {len(groups)} section groups in notebook")
            return groups

        return []

    def get_sections_in_group(self, group_id: str) -> List[Dict[str, Any]]:
        """
        Get all sections in a section group.

        Args:
            group_id: ID of the section group

        Returns:
            List of section objects
        """
        result = self._make_request(f'/me/onenote/sectionGroups/{group_id}/sections')

        if result and 'value' in result:
            return result['value']

        return []

    def get_pages(self, section_id: str) -> List[Dict[str, Any]]:
        """
        Get all pages in a section.

        Args:
            section_id: ID of the section

        Returns:
            List of page objects
        """
        result = self._make_request(f'/me/onenote/sections/{section_id}/pages')

        if result and 'value' in result:
            pages = result['value']
            self.logger.info(f"Found {len(pages)} pages in section")
            return pages

        return []

    def get_page_content(self, page_id: str) -> Optional[str]:
        """
        Get the HTML content of a page.

        Args:
            page_id: ID of the page

        Returns:
            HTML content as string
        """
        if not self._access_token:
            if not self.authenticate():
                return None

        url = f"{self.GRAPH_API_BASE}/me/onenote/pages/{page_id}/content"

        headers = {
            'Authorization': f'Bearer {self._access_token}',
            'Accept': 'text/html'
        }

        try:
            response = requests.get(url, headers=headers, timeout=60)

            if response.status_code == 401:
                self._access_token = None
                if self.authenticate():
                    return self.get_page_content(page_id)
                return None

            response.raise_for_status()
            return response.text

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get page content: {e}")
            return None

    def get_page_resources(self, page_id: str) -> List[Dict[str, Any]]:
        """
        Get resources (images, attachments) for a page.

        Args:
            page_id: ID of the page

        Returns:
            List of resource objects
        """
        result = self._make_request(f'/me/onenote/pages/{page_id}/content')

        # Resources are embedded in the HTML content
        # We'll extract them during content conversion
        return []

    def download_resource(self, resource_url: str) -> Optional[bytes]:
        """
        Download a resource (image, file) from OneNote.

        Args:
            resource_url: URL of the resource

        Returns:
            Binary content of the resource
        """
        if not self._access_token:
            if not self.authenticate():
                return None

        headers = {
            'Authorization': f'Bearer {self._access_token}'
        }

        try:
            response = requests.get(resource_url, headers=headers, timeout=60)

            if response.status_code == 401:
                self._access_token = None
                if self.authenticate():
                    return self.download_resource(resource_url)
                return None

            response.raise_for_status()
            return response.content

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to download resource: {e}")
            return None

    def validate_credentials(self) -> bool:
        """
        Validate that credentials are configured and working.

        Returns:
            True if credentials are valid
        """
        try:
            if not self.client_id:
                self.logger.error("Azure Client ID not configured")
                return False

            if self.authenticate():
                # Try to access user profile
                result = self._make_request('/me')
                if result and 'displayName' in result:
                    self.logger.info(f"Authenticated as: {result['displayName']}")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Credential validation failed: {e}")
            return False

    def get_all_notebooks_with_structure(self) -> List[Dict[str, Any]]:
        """
        Get all notebooks with their complete structure (sections, section groups, pages).

        Returns:
            List of notebooks with nested structure
        """
        notebooks = self.get_notebooks()

        for notebook in notebooks:
            notebook_id = notebook['id']
            notebook['sections'] = self.get_sections(notebook_id)
            notebook['sectionGroups'] = self.get_section_groups(notebook_id)

            # Get pages for each section
            for section in notebook['sections']:
                section['pages'] = self.get_pages(section['id'])

            # Recursively get sections in section groups
            for group in notebook['sectionGroups']:
                self._populate_section_group(group)

        return notebooks

    def _populate_section_group(self, group: Dict[str, Any]):
        """
        Recursively populate a section group with its sections and nested groups.

        Args:
            group: Section group object to populate
        """
        group['sections'] = self.get_sections_in_group(group['id'])

        # Get pages for each section
        for section in group['sections']:
            section['pages'] = self.get_pages(section['id'])

        # Get nested section groups
        result = self._make_request(f"/me/onenote/sectionGroups/{group['id']}/sectionGroups")

        if result and 'value' in result:
            group['sectionGroups'] = result['value']

            for nested_group in group['sectionGroups']:
                self._populate_section_group(nested_group)
        else:
            group['sectionGroups'] = []
