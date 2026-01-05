"""OPML import tool for bulk RSS feed ingestion."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional
import xml.etree.ElementTree as ET

from ..logger import get_logger


@dataclass(frozen=True)
class OPMLFeed:
    """Represents a feed entry extracted from an OPML file."""
    url: str
    title: str
    category: Optional[str]


class OPMLImporter:
    """Parses OPML files and extracts RSS/Atom feed URLs."""

    def __init__(self) -> None:
        self.logger = get_logger()

    def parse(self, opml_path: str) -> List[OPMLFeed]:
        """
        Parse an OPML file and return feed entries.

        Args:
            opml_path: Path to the OPML file.

        Returns:
            List of OPMLFeed entries.
        """
        path = Path(opml_path)
        if not path.exists():
            raise FileNotFoundError(f"OPML file not found: {path}")

        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            raise ValueError(f"Invalid OPML XML: {exc}") from exc

        root = tree.getroot()
        body = root.find("body")
        if body is None:
            body = root

        feeds: List[OPMLFeed] = []
        self._walk_outlines(body.findall("outline"), None, feeds)
        return feeds

    def group_by_category(self, feeds: Iterable[OPMLFeed]) -> Dict[str, List[OPMLFeed]]:
        """
        Group feeds by category (folder name).

        Args:
            feeds: Iterable of OPMLFeed entries.

        Returns:
            Dictionary mapping category names to feed lists.
        """
        grouped: Dict[str, List[OPMLFeed]] = {}
        for feed in feeds:
            category = feed.category or "uncategorized"
            grouped.setdefault(category, []).append(feed)
        return grouped

    def _walk_outlines(
        self,
        outlines: Iterable[ET.Element],
        category: Optional[str],
        feeds: List[OPMLFeed]
    ) -> None:
        """
        Recursively walk OPML outlines to collect feed URLs.

        Args:
            outlines: Iterable of outline elements.
            category: Current category (folder) name.
            feeds: Output list for collected feeds.
        """
        for outline in outlines:
            attrs = outline.attrib

            xml_url = (
                attrs.get("xmlUrl")
                or attrs.get("xmlurl")
                or attrs.get("xmlURL")
            )
            title = attrs.get("title") or attrs.get("text") or ""

            if xml_url:
                feeds.append(OPMLFeed(url=xml_url, title=title, category=category))
                continue

            next_category = title or category
            children = outline.findall("outline")
            if children:
                self._walk_outlines(children, next_category, feeds)
