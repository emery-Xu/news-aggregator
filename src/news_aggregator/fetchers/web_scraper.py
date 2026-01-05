"""Base class for custom web scrapers."""

from abc import ABC, abstractmethod
from typing import List
import httpx
from bs4 import BeautifulSoup

from ..models import Article
from ..logger import get_logger


class WebScraperBase(ABC):
    """Abstract base class for custom website scrapers."""

    def __init__(self):
        """Initialize web scraper."""
        self.logger = get_logger()

    @abstractmethod
    async def scrape(self) -> List[Article]:
        """
        Scrape articles from the target website.

        This method must be implemented by subclasses.

        Returns:
            List of Article objects scraped from the website
        """
        pass

    async def _fetch_html(self, url: str, timeout: float = 10.0) -> str:
        """
        Fetch HTML content from a URL.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            HTML content as string

        Raises:
            httpx.HTTPError: If request fails
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    def _parse_html(self, html: str) -> BeautifulSoup:
        """
        Parse HTML content with BeautifulSoup.

        Args:
            html: HTML content string

        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html, 'html.parser')

    def _extract_text(self, element) -> str:
        """
        Extract clean text from a BeautifulSoup element.

        Args:
            element: BeautifulSoup element

        Returns:
            Cleaned text content
        """
        if element is None:
            return ""
        return element.get_text(strip=True)

    def _extract_attribute(self, element, attribute: str) -> str:
        """
        Extract an attribute value from a BeautifulSoup element.

        Args:
            element: BeautifulSoup element
            attribute: Attribute name (e.g., 'href', 'src')

        Returns:
            Attribute value or empty string if not found
        """
        if element is None:
            return ""
        return element.get(attribute, "")
