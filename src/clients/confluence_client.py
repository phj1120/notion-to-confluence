"""Confluence API client with retry logic and proper error handling."""

import requests
from typing import Dict, Any, Optional
from requests.auth import HTTPBasicAuth

from src.core.config import ConfluenceConfig, APIConfig
from src.core.exceptions import ConfluenceAPIError, ValidationError
from src.core.logger import get_logger
from src.utils.retry_utils import retry_with_exponential_backoff, handle_api_error

logger = get_logger()


class ConfluenceClient:
    """Client for interacting with Confluence API."""

    def __init__(self, config: ConfluenceConfig, api_config: APIConfig):
        """Initialize Confluence client.

        Args:
            config: Confluence configuration
            api_config: API configuration for timeouts and retries
        """
        self.config = config
        self.api_config = api_config
        self.auth = HTTPBasicAuth(config.username, config.api_token)

    def _validate_title(self, title: str) -> None:
        """Validate page title.

        Args:
            title: Page title

        Raises:
            ValidationError: If title is invalid
        """
        if not title or not isinstance(title, str):
            raise ValidationError(f"Invalid page title: {title}")

        if len(title) > 255:
            raise ValidationError(
                f"Page title too long ({len(title)} chars). Maximum 255 characters allowed."
            )

    @retry_with_exponential_backoff(max_retries=3, backoff_factor=2.0)
    def update_page(
        self,
        page_id: str,
        title: str,
        content: str,
        version: int
    ) -> Dict[str, Any]:
        """Update an existing page in Confluence.

        Args:
            page_id: Confluence page ID
            title: Page title
            content: Page content in Confluence storage format
            version: Current page version number

        Returns:
            Updated page data dictionary

        Raises:
            ValidationError: If title is invalid
            ConfluenceAPIError: If API request fails
        """
        self._validate_title(title)

        url = f"{self.config.url}/wiki/rest/api/content/{page_id}"
        logger.info(f"Updating Confluence page: {page_id} (v{version} -> v{version + 1})")

        page_data = {
            "type": "page",
            "title": title,
            "version": {"number": version + 1},
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage"
                }
            }
        }

        try:
            response = requests.put(
                url,
                json=page_data,
                auth=self.auth,
                timeout=self.api_config.timeout,
            )

            if not response.ok:
                handle_api_error(response, "Confluence API")

            result = response.json()
            logger.info(f"Successfully updated page: {page_id}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update page '{page_id}': {e}")
            raise ConfluenceAPIError(f"Failed to update page: {e}")

    @retry_with_exponential_backoff(max_retries=3, backoff_factor=2.0)
    def get_page_by_id(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Get a page by its ID.

        Args:
            page_id: Confluence page ID

        Returns:
            Page data dictionary if found, None otherwise

        Raises:
            ConfluenceAPIError: If API request fails
        """
        url = f"{self.config.url}/wiki/rest/api/content/{page_id}"
        params = {"expand": "version"}

        logger.debug(f"Fetching page by ID: {page_id}")

        try:
            response = requests.get(
                url,
                params=params,
                auth=self.auth,
                timeout=self.api_config.timeout,
            )

            if response.status_code == 404:
                logger.debug(f"Page {page_id} not found")
                return None

            if not response.ok:
                handle_api_error(response, "Confluence API")

            data = response.json()
            logger.debug(f"Found page: {page_id}")
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch page '{page_id}': {e}")
            raise ConfluenceAPIError(f"Failed to fetch page: {e}")

    @retry_with_exponential_backoff(max_retries=3, backoff_factor=2.0)
    def upload_attachment(
        self,
        page_id: str,
        filename: str,
        file_data: bytes,
        content_type: str = "application/octet-stream"
    ) -> Dict[str, Any]:
        """Upload an attachment to a Confluence page.

        Args:
            page_id: Confluence page ID
            filename: Name for the attachment
            file_data: Binary file data
            content_type: MIME type of the file

        Returns:
            Attachment data dictionary

        Raises:
            ConfluenceAPIError: If API request fails
        """
        url = f"{self.config.url}/wiki/rest/api/content/{page_id}/child/attachment"
        logger.info(f"Uploading attachment '{filename}' to page {page_id}")

        # Check if attachment already exists and delete it
        try:
            existing_attachments = requests.get(
                url,
                auth=self.auth,
                timeout=self.api_config.timeout,
            )
            if existing_attachments.ok:
                data = existing_attachments.json()
                for attachment in data.get("results", []):
                    if attachment.get("title") == filename:
                        attachment_id = attachment.get("id")
                        logger.info(f"Deleting existing attachment: {attachment_id}")
                        # Update existing attachment instead of creating new one
                        url = f"{self.config.url}/wiki/rest/api/content/{page_id}/child/attachment/{attachment_id}/data"
                        break
        except Exception as e:
            logger.warning(f"Failed to check for existing attachments: {e}")

        try:
            files = {"file": (filename, file_data, content_type)}
            headers = {"X-Atlassian-Token": "nocheck"}  # Required to prevent XSRF

            response = requests.post(
                url,
                files=files,
                headers=headers,
                auth=self.auth,
                timeout=self.api_config.timeout,
            )

            if not response.ok:
                handle_api_error(response, "Confluence API")

            result = response.json()
            logger.info(f"Successfully uploaded attachment: {filename}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to upload attachment '{filename}': {e}")
            raise ConfluenceAPIError(f"Failed to upload attachment: {e}")

    def create_or_update_page(
        self,
        title: str,
        content: str,
        target_page_id: str
    ) -> Dict[str, Any]:
        """Update an existing Confluence page.

        Args:
            title: Page title (will use existing page's title to avoid conflicts)
            content: Page content in Confluence storage format
            target_page_id: Target page ID to update (required)

        Returns:
            Updated page data dictionary

        Raises:
            ValidationError: If title is invalid
            ConfluenceAPIError: If API request fails or page not found
        """
        logger.info(f"Updating Confluence page: {target_page_id}")
        existing_page = self.get_page_by_id(target_page_id)

        if not existing_page:
            raise ConfluenceAPIError(f"Page {target_page_id} not found. Please provide a valid Confluence page URL in mapping.csv")

        version = existing_page["version"]["number"]
        # Use existing page title to avoid conflicts
        existing_title = existing_page.get("title", title)
        logger.info(f"Keeping existing title: {existing_title}")

        return self.update_page(target_page_id, existing_title, content, version)
