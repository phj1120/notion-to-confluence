"""Retry utilities with exponential backoff for API calls."""

import time
from functools import wraps
from typing import Callable, TypeVar, Type, Tuple
import requests

from src.core.logger import get_logger
from src.core.exceptions import NotionAPIError, ConfluenceAPIError

logger = get_logger()

T = TypeVar("T")


def retry_with_exponential_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (requests.exceptions.RequestException,),
) -> Callable:
    """Decorator to retry functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff
        retry_exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) reached for {func.__name__}",
                            extra={"error": str(e)},
                        )
                        break

                    wait_time = backoff_factor ** attempt
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{max_retries} for {func.__name__} "
                        f"after {wait_time:.1f}s",
                        extra={"error": str(e)},
                    )
                    time.sleep(wait_time)

            raise last_exception

        return wrapper

    return decorator


def handle_api_error(response: requests.Response, api_type: str = "API") -> None:
    """Handle API error responses.

    Args:
        response: requests Response object
        api_type: Type of API (for error messages)

    Raises:
        NotionAPIError: For Notion API errors
        ConfluenceAPIError: For Confluence API errors
    """
    try:
        error_data = response.json()
        error_message = error_data.get("message", response.text)
    except ValueError:
        error_message = response.text

    details = {
        "status_code": response.status_code,
        "url": response.url,
        "response": error_message,
    }

    logger.error(
        f"{api_type} error: {response.status_code}",
        extra=details,
    )

    if "Notion" in api_type:
        raise NotionAPIError(
            f"{api_type} request failed: {error_message}",
            status_code=response.status_code,
            details=details,
        )
    else:
        raise ConfluenceAPIError(
            f"{api_type} request failed: {error_message}",
            status_code=response.status_code,
            details=details,
        )
