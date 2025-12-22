#!/usr/bin/env python3
"""Main migration script for Notion to Confluence migration.

This script reads configuration from mapping.csv, migrates pages
from Notion to Confluence, and tracks the migration history.
"""

import sys
from typing import Tuple, Optional
from dataclasses import dataclass

from src.core.config import AppConfig
from src.clients.notion_client import NotionClient
from src.clients.confluence_client import ConfluenceClient
from src.utils.format_converter import NotionToConfluenceConverter
from src.utils.csv_manager import MappingManager, HistoryManager
from src.core.logger import setup_logger, get_logger
from src.core.exceptions import (
    MigrationError,
    ConfigurationError,
    NotionAPIError,
    ConfluenceAPIError,
)


@dataclass
class MigrationResult:
    """Result of a single page migration."""

    page_id: str
    success: bool
    confluence_url: Optional[str] = None
    error_message: Optional[str] = None


class MigrationService:
    """Service for managing the entire migration process."""

    def __init__(self, config: AppConfig):
        """Initialize migration service.

        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = get_logger()

        # Initialize clients
        self.notion_client = NotionClient(config.notion, config.api)
        self.confluence_client = ConfluenceClient(config.confluence, config.api)
        # Note: converter will be created per-page with page_id for image uploads

        # Initialize CSV managers
        self.mapping_manager = MappingManager(config.files.mapping_csv)
        self.history_manager = HistoryManager(config.files.history_csv)

    def migrate_page(self, mapping: dict) -> MigrationResult:
        """Migrate a single page from Notion to Confluence.

        Args:
            mapping: Mapping dictionary from CSV

        Returns:
            MigrationResult with success/failure information
        """
        page_id = mapping["id"]
        notion_url = mapping["notion_url"]
        confluence_url = mapping.get("confluence_url", "")

        self.logger.info("=" * 60)
        self.logger.info(f"Migrating page: {page_id}")
        self.logger.info("=" * 60)

        try:
            # Extract Notion page ID from URL
            notion_page_id = self.mapping_manager.extract_notion_page_id(notion_url)
            self.logger.info(f"Notion page ID: {notion_page_id}")

            # Extract target Confluence page ID if specified
            target_page_id = self.mapping_manager.extract_confluence_page_id(confluence_url)
            if target_page_id:
                self.logger.info(f"Target Confluence page ID: {target_page_id}")

            # Get page from Notion
            self.logger.info("Fetching page from Notion...")
            page = self.notion_client.get_page(notion_page_id)

            # Get page title
            title = self.notion_client.get_page_title(page)
            self.logger.info(f"Page title: {title}")

            # Get page blocks
            self.logger.info("Fetching page blocks...")
            blocks = self.notion_client.get_blocks(notion_page_id)
            self.logger.info(f"Found {len(blocks)} blocks")

            # Require target_page_id
            if not target_page_id:
                raise MigrationError(
                    "Target Confluence page URL is required in mapping.csv. "
                    "Please create the page in Confluence first and add its URL to mapping.csv."
                )

            # Convert to Confluence format with image support
            self.logger.info("Converting format...")
            converter = NotionToConfluenceConverter(
                confluence_client=self.confluence_client,
                page_id=target_page_id
            )
            confluence_content = converter.convert_blocks(blocks)

            # Update existing page
            self.logger.info("Updating existing page in Confluence...")
            result = self.confluence_client.create_or_update_page(
                title=title,
                content=confluence_content,
                target_page_id=target_page_id
            )

            # Get the actual space from the result (pages can be in different spaces)
            space_key = result.get("space", {}).get("key", "")
            confluence_url = (
                f"{self.config.confluence.url}/wiki/spaces/"
                f"{space_key}/pages/{result['id']}"
            )

            self.logger.info(f"✓ Successfully migrated!")
            self.logger.info(f"  Confluence URL: {confluence_url}")

            return MigrationResult(
                page_id=page_id,
                success=True,
                confluence_url=confluence_url,
            )

        except (NotionAPIError, ConfluenceAPIError, MigrationError) as e:
            self.logger.error(f"✗ Migration failed: {e}")
            return MigrationResult(
                page_id=page_id,
                success=False,
                error_message=str(e),
            )
        except Exception as e:
            self.logger.exception(f"✗ Unexpected error: {e}")
            return MigrationResult(
                page_id=page_id,
                success=False,
                error_message=f"Unexpected error: {e}",
            )

    def run(self) -> int:
        """Run the migration process for all pages marked for update.

        Returns:
            Exit code (0 for success, 1 for any failures)
        """
        # Get pages to update
        pages_to_update = self.mapping_manager.get_pages_to_update()

        if not pages_to_update:
            self.logger.warning(
                "No pages marked for update (should_update = true) in mapping.csv"
            )
            return 0

        # Migrate pages
        self.logger.info(f"\nStarting migration of {len(pages_to_update)} page(s)...")

        success_count = 0
        error_count = 0
        results = []

        for mapping in pages_to_update:
            result = self.migrate_page(mapping)
            results.append(result)

            # Record in history
            self.history_manager.add_record(result.page_id, result.success)

            if result.success:
                # Update mapping with new timestamp and Confluence URL
                self.mapping_manager.update_last_updated(
                    result.page_id, result.confluence_url
                )
                success_count += 1
            else:
                error_count += 1

        # Print summary
        self.logger.info("\n" + "=" * 60)
        self.logger.info("Migration Summary")
        self.logger.info("=" * 60)
        self.logger.info(f"Total pages: {len(pages_to_update)}")
        self.logger.info(f"Successful: {success_count}")
        self.logger.info(f"Failed: {error_count}")
        self.logger.info("=" * 60 + "\n")

        return 1 if error_count > 0 else 0


def main() -> int:
    """Main entry point for the migration script.

    Returns:
        Exit code
    """
    # Setup logging
    setup_logger()
    logger = get_logger()

    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = AppConfig.from_env()

        # Run migration
        service = MigrationService(config)
        return service.run()

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
