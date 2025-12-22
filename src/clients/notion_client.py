"""Notion API client with retry logic and proper error handling."""

import requests
from typing import Dict, List, Any, Optional

from src.core.config import NotionConfig, APIConfig
from src.core.exceptions import NotionAPIError, ValidationError
from src.core.logger import get_logger
from src.utils.retry_utils import retry_with_exponential_backoff, handle_api_error

logger = get_logger()


class NotionClient:
    """Client for interacting with Notion API."""

    def __init__(self, config: NotionConfig, api_config: APIConfig):
        """Initialize Notion client.

        Args:
            config: Notion configuration
            api_config: API configuration for timeouts and retries
        """
        self.config = config
        self.api_config = api_config
        self.headers = {
            "Authorization": f"Bearer {config.api_token}",
            "Notion-Version": config.api_version,
            "Content-Type": "application/json",
        }

    def _validate_page_id(self, page_id: str) -> None:
        """Validate page ID format.

        Args:
            page_id: Notion page ID

        Raises:
            ValidationError: If page ID is invalid
        """
        if not page_id or not isinstance(page_id, str):
            raise ValidationError(f"Invalid page ID: {page_id}")

        # Remove hyphens for validation
        clean_id = page_id.replace("-", "")
        if len(clean_id) != 32 or not clean_id.isalnum():
            raise ValidationError(
                f"Invalid Notion page ID format: {page_id}. "
                "Expected 32 character alphanumeric string (with optional hyphens)"
            )

    @retry_with_exponential_backoff(max_retries=3, backoff_factor=2.0)
    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get page metadata from Notion.

        Args:
            page_id: Notion page ID

        Returns:
            Page metadata dictionary

        Raises:
            ValidationError: If page ID is invalid
            NotionAPIError: If API request fails
        """
        self._validate_page_id(page_id)

        url = f"{self.config.base_url}/pages/{page_id}"
        logger.info(f"Fetching page metadata: {page_id}")

        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.api_config.timeout,
            )

            if not response.ok:
                handle_api_error(response, "Notion API")

            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch page {page_id}: {e}")
            raise NotionAPIError(f"Failed to fetch page: {e}")

    @retry_with_exponential_backoff(max_retries=3, backoff_factor=2.0)
    def get_blocks(self, block_id: str) -> List[Dict[str, Any]]:
        """Get all blocks (content) from a Notion page recursively.

        Args:
            block_id: Block ID (typically the page ID)

        Returns:
            List of block dictionaries

        Raises:
            NotionAPIError: If API request fails
        """
        all_blocks = []
        url = f"{self.config.base_url}/blocks/{block_id}/children"

        has_more = True
        start_cursor: Optional[str] = None

        logger.info(f"Fetching blocks for: {block_id}")

        while has_more:
            params = {"page_size": self.api_config.page_size}
            if start_cursor:
                params["start_cursor"] = start_cursor

            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=self.api_config.timeout,
                )

                if not response.ok:
                    handle_api_error(response, "Notion API")

                data = response.json()

                blocks = data.get("results", [])
                all_blocks.extend(blocks)

                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")

                # Get children blocks recursively
                for block in blocks:
                    if block.get("has_children"):
                        children = self.get_blocks(block["id"])
                        block["children"] = children

            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch blocks for {block_id}: {e}")
                raise NotionAPIError(f"Failed to fetch blocks: {e}")

        logger.info(f"Fetched {len(all_blocks)} blocks")
        return all_blocks

    def get_page_title(self, page: Dict[str, Any]) -> str:
        """Extract title from page metadata.

        Args:
            page: Page metadata dictionary

        Returns:
            Page title string, or "Untitled" if not found
        """
        properties = page.get("properties", {})

        # Try to find title property
        for prop_value in properties.values():
            if prop_value.get("type") == "title":
                title_array = prop_value.get("title", [])
                if title_array:
                    title = "".join([t.get("plain_text", "") for t in title_array])
                    logger.debug(f"Extracted title: {title}")
                    return title

        logger.warning("No title found, using 'Untitled'")
        return "Untitled"
