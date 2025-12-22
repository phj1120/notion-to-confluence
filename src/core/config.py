"""Configuration management for the migration tool."""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

from src.core.exceptions import ConfigurationError


@dataclass(frozen=True)
class NotionConfig:
    """Configuration for Notion API."""

    api_token: str
    api_version: str = "2022-06-28"
    base_url: str = "https://api.notion.com/v1"

    def __post_init__(self):
        if not self.api_token:
            raise ConfigurationError("Notion API token is required")


@dataclass(frozen=True)
class ConfluenceConfig:
    """Configuration for Confluence API."""

    url: str
    username: str
    api_token: str

    def __post_init__(self):
        if not all([self.url, self.username, self.api_token]):
            raise ConfigurationError(
                "Required Confluence configuration missing: "
                "url, username, api_token"
            )


@dataclass(frozen=True)
class APIConfig:
    """API call configuration."""

    timeout: int = 30
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    page_size: int = 100


@dataclass(frozen=True)
class FileConfig:
    """File paths configuration."""

    mapping_csv: str = "mapping.csv"
    history_csv: str = "history.csv"
    env_file: str = ".env"


@dataclass(frozen=True)
class AppConfig:
    """Application configuration."""

    notion: NotionConfig
    confluence: ConfluenceConfig
    api: APIConfig = APIConfig()
    files: FileConfig = FileConfig()

    @classmethod
    def from_env(cls, env_file: str = ".env") -> "AppConfig":
        """Load configuration from environment variables.

        Args:
            env_file: Path to .env file

        Returns:
            AppConfig instance

        Raises:
            ConfigurationError: If required environment variables are missing
        """
        load_dotenv(env_file)

        required_vars = {
            "NOTION_API_TOKEN": "Notion API token",
            "CONFLUENCE_URL": "Confluence URL",
            "CONFLUENCE_USERNAME": "Confluence username",
            "CONFLUENCE_API_TOKEN": "Confluence API token",
        }

        missing_vars = []
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing_vars.append(f"{var} ({description})")

        if missing_vars:
            raise ConfigurationError(
                f"Missing required environment variables:\n" + "\n".join(f"  - {v}" for v in missing_vars)
            )

        notion_config = NotionConfig(
            api_token=os.getenv("NOTION_API_TOKEN"),
            api_version=os.getenv("NOTION_API_VERSION", "2022-06-28"),
        )

        confluence_config = ConfluenceConfig(
            url=os.getenv("CONFLUENCE_URL").rstrip("/"),
            username=os.getenv("CONFLUENCE_USERNAME"),
            api_token=os.getenv("CONFLUENCE_API_TOKEN"),
        )

        api_config = APIConfig(
            timeout=int(os.getenv("API_TIMEOUT", "30")),
            max_retries=int(os.getenv("API_MAX_RETRIES", "3")),
            retry_backoff_factor=float(os.getenv("API_RETRY_BACKOFF", "2.0")),
            page_size=int(os.getenv("API_PAGE_SIZE", "100")),
        )

        file_config = FileConfig(
            mapping_csv=os.getenv("MAPPING_CSV", "mapping.csv"),
            history_csv=os.getenv("HISTORY_CSV", "history.csv"),
            env_file=env_file,
        )

        return cls(
            notion=notion_config,
            confluence=confluence_config,
            api=api_config,
            files=file_config,
        )
