"""Google Docs integration service for reading tracking documents."""

import os
import pickle
from typing import Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the token file.
SCOPES = ['https://www.googleapis.com/auth/documents.readonly']


class DocsService:
    """Service for interacting with Google Docs API."""

    def __init__(self, credentials_path: str, token_path: str):
        """
        Initialize Docs Service.

        Args:
            credentials_path: Path to OAuth2 credentials JSON file
            token_path: Path to store/retrieve the token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None

    def authenticate(self) -> None:
        """Authenticate with Google Docs API."""
        creds = None

        # Token stores the user's access and refresh tokens
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        try:
            self.service = build('docs', 'v1', credentials=creds)
            logger.info("Successfully authenticated with Google Docs API")
        except HttpError as error:
            logger.error(f"Failed to build Docs service: {error}")
            raise

    def get_document_content(self, document_id: str) -> str:
        """
        Retrieve the full text content of a Google Doc.

        Args:
            document_id: The ID of the document to retrieve

        Returns:
            String containing the full document text

        Raises:
            HttpError: If the API request fails
        """
        if not self.service:
            self.authenticate()

        try:
            logger.info(f"Fetching document: {document_id}")

            # Retrieve the documents contents from the Docs service
            document = self.service.documents().get(documentId=document_id).execute()

            # Extract text from document structure
            doc_content = self._extract_text_from_document(document)

            logger.info(f"Successfully retrieved document ({len(doc_content)} characters)")
            return doc_content

        except HttpError as error:
            logger.error(f"An error occurred while fetching document: {error}")
            raise

    def _extract_text_from_document(self, document: Dict) -> str:
        """
        Extract plain text from a Google Docs document structure.

        Args:
            document: The document resource from the API

        Returns:
            Plain text content of the document
        """
        content = []

        # Process each structural element in the document
        for element in document.get('body', {}).get('content', []):
            if 'paragraph' in element:
                paragraph = element['paragraph']

                # Extract text from each element in the paragraph
                for elem in paragraph.get('elements', []):
                    if 'textRun' in elem:
                        text_run = elem['textRun']
                        content.append(text_run.get('content', ''))

            elif 'table' in element:
                # Extract text from table cells
                table = element['table']
                for row in table.get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        for cell_element in cell.get('content', []):
                            if 'paragraph' in cell_element:
                                paragraph = cell_element['paragraph']
                                for elem in paragraph.get('elements', []):
                                    if 'textRun' in elem:
                                        text_run = elem['textRun']
                                        content.append(text_run.get('content', ''))

        return ''.join(content)

    def get_document_metadata(self, document_id: str) -> Dict:
        """
        Get metadata about a Google Doc.

        Args:
            document_id: The ID of the document

        Returns:
            Dictionary containing document metadata

        Raises:
            HttpError: If the API request fails
        """
        if not self.service:
            self.authenticate()

        try:
            document = self.service.documents().get(documentId=document_id).execute()

            return {
                'title': document.get('title'),
                'documentId': document.get('documentId'),
                'revisionId': document.get('revisionId'),
                'createdTime': document.get('createdTime'),
                'modifiedTime': document.get('modifiedTime')
            }

        except HttpError as error:
            logger.error(f"An error occurred while fetching document metadata: {error}")
            raise

    def search_document(self, document_id: str, search_term: str) -> bool:
        """
        Check if a search term exists in the document.

        Args:
            document_id: The ID of the document
            search_term: Term to search for

        Returns:
            True if term is found, False otherwise
        """
        content = self.get_document_content(document_id)
        return search_term.lower() in content.lower()

    def validate_document_structure(self, document_id: str, required_sections: list) -> Dict:
        """
        Validate that a document contains required sections.

        Args:
            document_id: The ID of the document to validate
            required_sections: List of section names that must be present

        Returns:
            Dictionary with validation results
        """
        content = self.get_document_content(document_id)

        validation = {
            'valid': True,
            'missing_sections': [],
            'found_sections': []
        }

        for section in required_sections:
            section_marker = f"[{section}]"
            if section_marker in content:
                validation['found_sections'].append(section)
            else:
                validation['valid'] = False
                validation['missing_sections'].append(section)

        return validation
