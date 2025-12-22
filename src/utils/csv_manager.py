"""CSV file managers for mapping and history tracking."""

import csv
import os
import re
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from src.core.logger import get_logger
from src.core.exceptions import CSVError, ValidationError

logger = get_logger()


class MappingManager:
    """Manage mapping.csv file for page migrations.

    The mapping file tracks the relationship between Notion pages
    and their corresponding Confluence pages, along with update status.
    """

    FIELDNAMES = [
        "id",
        "notion_url",
        "confluence_url",
        "should_update",
        "last_updated"
    ]

    # Notion URL patterns - supports multiple formats:
    # 1. https://www.notion.so/Page-Title-{id}
    # 2. https://www.notion.so/workspace/{id}
    # 3. https://www.notion.so/{id}
    NOTION_URL_PATTERNS = [
        re.compile(r"https://(?:www\.)?notion\.so/.+-([a-f0-9]{32})"),  # With title
        re.compile(r"https://(?:www\.)?notion\.so/[^/]+/([a-f0-9]{32})"),  # workspace/id
        re.compile(r"https://(?:www\.)?notion\.so/([a-f0-9]{32})"),  # Just ID
    ]

    def __init__(self, csv_path: str = "mapping.csv"):
        """Initialize mapping manager.

        Args:
            csv_path: Path to mapping CSV file
        """
        self.csv_path = Path(csv_path)

    def read_mappings(self) -> List[Dict[str, str]]:
        """Read all mappings from CSV file.

        Returns:
            List of mapping dictionaries

        Raises:
            CSVError: If CSV file cannot be read
        """
        if not self.csv_path.exists():
            logger.warning(f"{self.csv_path} not found. Creating empty mapping file.")
            self._create_empty_file()
            return []

        try:
            mappings = []
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row_num, row in enumerate(reader, start=2):
                    # Validate row has required fields
                    if not all(field in row for field in self.FIELDNAMES):
                        logger.warning(f"Row {row_num} missing required fields")
                        continue
                    mappings.append(row)

            logger.info(f"Read {len(mappings)} mappings from {self.csv_path}")
            return mappings

        except (IOError, csv.Error) as e:
            logger.error(f"Failed to read {self.csv_path}: {e}")
            raise CSVError(f"Failed to read mapping file: {e}")

    def get_pages_to_update(self) -> List[Dict[str, str]]:
        """Get only pages that should be updated (should_update = true).

        Returns:
            List of mappings where should_update is true
        """
        all_mappings = self.read_mappings()
        pages = [
            mapping for mapping in all_mappings
            if mapping.get("should_update", "").lower() in ["true", "yes", "1"]
        ]
        logger.info(f"Found {len(pages)} pages marked for update")
        return pages

    def update_last_updated(
        self,
        page_id: str,
        confluence_url: Optional[str] = None
    ) -> None:
        """Update last_updated timestamp for a specific page.

        Args:
            page_id: Page identifier
            confluence_url: Optional Confluence URL to update

        Raises:
            CSVError: If update fails
        """
        mappings = self.read_mappings()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        found = False
        for mapping in mappings:
            if mapping["id"] == page_id:
                mapping["last_updated"] = current_time
                if confluence_url:
                    mapping["confluence_url"] = confluence_url
                found = True
                logger.debug(f"Updated mapping for page {page_id}")
                break

        if not found:
            logger.warning(f"Page {page_id} not found in mappings")

        self._write_mappings(mappings)

    def _write_mappings(self, mappings: List[Dict[str, str]]) -> None:
        """Write mappings back to CSV file.

        Args:
            mappings: List of mapping dictionaries

        Raises:
            CSVError: If write fails
        """
        try:
            with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
                writer.writerows(mappings)
        except (IOError, csv.Error) as e:
            logger.error(f"Failed to write {self.csv_path}: {e}")
            raise CSVError(f"Failed to write mapping file: {e}")

    def _create_empty_file(self) -> None:
        """Create an empty mapping CSV file with headers.

        Raises:
            CSVError: If file creation fails
        """
        try:
            with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
            logger.info(f"Created empty mapping file: {self.csv_path}")
        except (IOError, csv.Error) as e:
            logger.error(f"Failed to create {self.csv_path}: {e}")
            raise CSVError(f"Failed to create mapping file: {e}")

    def extract_notion_page_id(self, notion_url: str) -> str:
        """Extract page ID from Notion URL.

        Supports multiple Notion URL formats:
        - https://www.notion.so/Page-Title-{id}
        - https://www.notion.so/workspace/{id}
        - https://www.notion.so/{id}

        Args:
            notion_url: Notion page URL

        Returns:
            32-character page ID

        Raises:
            ValidationError: If URL format is invalid
        """
        # Remove query parameters
        clean_url = notion_url.split("?")[0]

        # Try each regex pattern
        for pattern in self.NOTION_URL_PATTERNS:
            match = pattern.search(clean_url)
            if match:
                page_id = match.group(1)
                logger.debug(f"Extracted page ID from URL: {page_id}")
                return page_id

        # Fallback: extract last segment and validate
        segments = clean_url.split("/")
        if segments:
            last_segment = segments[-1]
            # Check if it's a valid 32-char hex ID
            if len(last_segment) == 32 and all(c in "0123456789abcdef" for c in last_segment.lower()):
                logger.debug(f"Extracted page ID from last segment: {last_segment}")
                return last_segment

        raise ValidationError(
            f"Invalid Notion URL format: {notion_url}. "
            "Expected format: https://www.notion.so/Page-Title-{{32-char-id}} or similar"
        )

    def extract_confluence_page_id(self, confluence_url: str) -> Optional[str]:
        """Extract page ID from Confluence URL.

        Args:
            confluence_url: Confluence page URL

        Returns:
            Page ID if found, None otherwise
        """
        if not confluence_url:
            return None

        # Confluence URL format: .../pages/{page_id}/...
        # Example: https://plateer.atlassian.net/wiki/spaces/SPACE/pages/1187872771/Title
        parts = confluence_url.split("/pages/")
        if len(parts) >= 2:
            # Get the page ID (numeric part after /pages/)
            page_id_part = parts[1].split("/")[0]
            if page_id_part.isdigit():
                logger.debug(f"Extracted Confluence page ID: {page_id_part}")
                return page_id_part

        logger.warning(f"Could not extract page ID from Confluence URL: {confluence_url}")
        return None


class HistoryManager:
    """Manage history.csv file for migration logs.

    The history file maintains a chronological log of all migration
    attempts, including success/failure status.
    """

    FIELDNAMES = ["id", "timestamp", "success"]

    def __init__(self, csv_path: str = "history.csv"):
        """Initialize history manager.

        Args:
            csv_path: Path to history CSV file
        """
        self.csv_path = Path(csv_path)

        # Create file if it doesn't exist
        if not self.csv_path.exists():
            self._create_empty_file()

    def add_record(self, page_id: str, success: bool) -> None:
        """Add a migration record to history.

        Args:
            page_id: Page identifier
            success: Whether migration was successful

        Raises:
            CSVError: If record cannot be added
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        success_str = "success" if success else "failure"

        try:
            with open(self.csv_path, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writerow({
                    "id": page_id,
                    "timestamp": timestamp,
                    "success": success_str
                })
            logger.debug(f"Added history record: {page_id} - {success_str}")
        except (IOError, csv.Error) as e:
            logger.error(f"Failed to add history record: {e}")
            raise CSVError(f"Failed to add history record: {e}")

    def get_history(self, page_id: Optional[str] = None) -> List[Dict[str, str]]:
        """Get migration history.

        Args:
            page_id: Optional page ID to filter by

        Returns:
            List of history records

        Raises:
            CSVError: If history cannot be read
        """
        if not self.csv_path.exists():
            logger.warning(f"{self.csv_path} not found")
            return []

        try:
            history = []
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if page_id is None or row.get("id") == page_id:
                        history.append(row)

            logger.debug(f"Retrieved {len(history)} history records")
            return history

        except (IOError, csv.Error) as e:
            logger.error(f"Failed to read {self.csv_path}: {e}")
            raise CSVError(f"Failed to read history file: {e}")

    def _create_empty_file(self) -> None:
        """Create an empty history CSV file with headers.

        Raises:
            CSVError: If file creation fails
        """
        try:
            with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
            logger.info(f"Created empty history file: {self.csv_path}")
        except (IOError, csv.Error) as e:
            logger.error(f"Failed to create {self.csv_path}: {e}")
            raise CSVError(f"Failed to create history file: {e}")
