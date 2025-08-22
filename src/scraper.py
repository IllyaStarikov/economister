"""Main scraper orchestrator for The Economist."""

from typing import List, Optional

from config import (
    ARTICLE_LOAD_WAIT_TIME, ECONOMIST_URL, MIN_PARAGRAPHS_PER_ARTICLE
)
from models import Article, Edition
from utils import (
    extract_date_from_cover_url, extract_date_from_text,
    save_debug_html
)
from browser import BrowserManager
from content_extractor import ContentExtractor


class EconomistScraper:
    """Orchestrates scraping of The Economist website."""

    def __init__(self, debug: bool = False):
        """Initialize the scraper.

        Args:
            debug: Enable debug mode.
        """
        self.debug = debug
        self.browser = BrowserManager()
        self.extractor = ContentExtractor(debug=debug)
        self.edition = Edition()

    def initialize(self) -> None:
        """Initialize browser and authenticate."""
        self.browser.setup()
        self.browser.login()

    def scrape_weekly_edition(self) -> Edition:
        """Scrape the weekly edition page for article links.

        Returns:
            Edition object with article metadata.
        """
        print("Getting article URLs...")
        html = self.browser.navigate(ECONOMIST_URL)
        save_debug_html("weekly_edition", html, self.debug)

        # Extract edition date
        self._extract_edition_date(html)

        # Extract cover URL
        cover_url = self.extractor.extract_cover_url(html)
        if cover_url:
            self.edition.cover_url = cover_url
            if self.debug:
                print(f"Found cover: {cover_url}")

        # Extract article links
        article_links = self.extractor.extract_article_links(html)

        print(f"Found {len(article_links)} unique articles")

        # Create Article objects with metadata
        for link_info in article_links:
            article = Article(
                title=link_info['title'],
                url=link_info['url'],
                section=link_info['section']
            )
            self.edition.articles.append(article)

        self._print_section_counts()

        return self.edition

    def scrape_article(self, article: Article) -> bool:
        """Scrape full content for an article.

        Args:
            article: Article object to populate with content.

        Returns:
            True if article was successfully scraped.
        """
        if not article.url:
            return False

        try:
            html = self.browser.navigate(
                article.url,
                wait_time=ARTICLE_LOAD_WAIT_TIME
            )
            save_debug_html(article.title or "article", html, self.debug)

            # Extract content into the same article object
            extracted = self.extractor.extract_article(html, article.url)

            # Update article with extracted content
            if not article.title:
                article.title = extracted.title
            article.subtitle = extracted.subtitle
            article.content_blocks = extracted.content_blocks

            # Validate minimum content
            if article.paragraph_count < MIN_PARAGRAPHS_PER_ARTICLE:
                print(f"  ⚠ Skipped (only {article.paragraph_count} "
                      f"paragraphs)")
                return False

            print(f"  ✓ Extracted {article.paragraph_count} paragraphs, "
                  f"{article.image_count} images")
            return True

        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False

    def scrape_articles(self, limit: Optional[int] = None) -> List[Article]:
        """Scrape multiple articles with optional limit.

        Args:
            limit: Maximum number of articles to scrape.

        Returns:
            List of successfully scraped articles.
        """
        articles = self.edition.articles

        if limit and limit > 0:
            original_count = len(articles)
            articles = articles[:limit]
            print(f"\n📎 Limiting to {len(articles)} articles "
                  f"(out of {original_count} available)")

        successful_articles = []

        for i, article in enumerate(articles, 1):
            section = article.section or "Unknown"
            title = (article.title or "Untitled")[:50]
            print(f"\n[{i}/{len(articles)}] [{section}] {title}...")

            if self.scrape_article(article):
                successful_articles.append(article)

        return successful_articles

    def cleanup(self) -> None:
        """Clean up resources."""
        self.browser.quit()

    def _extract_edition_date(self, html: str) -> None:
        """Extract and set the edition date from the page."""
        # Try to find date from cover image
        cover_url = self.extractor.extract_cover_url(html)
        if cover_url:
            date = extract_date_from_cover_url(cover_url)
            if date:
                self.edition.date = date
                print(f"Weekly edition date: {date}")

                # Track cover pattern
                import re
                match = re.search(r'/(\d{8})_', cover_url)
                if match:
                    self.extractor.cover_patterns.add(match.group(1))
                    print(f"Tracking cover pattern: {match.group(1)}")

                return

        # Fallback: find date from page text
        date = extract_date_from_text(html)
        if date:
            self.edition.date = date
            print(f"Weekly edition date: {date}")

    def _print_section_counts(self) -> None:
        """Print article counts by section."""
        from config import SECTION_ORDER

        sections = self.edition.articles_by_section()

        print("\nArticles by section:")
        for section in SECTION_ORDER:
            if section in sections:
                print(f"  {section}: {len(sections[section])}")

        if 'Other' in sections:
            print(f"  Other: {len(sections['Other'])}")
            if self.debug:
                print("\n  Uncategorized articles:")
                for article in sections['Other']:
                    if article.url:
                        url_part = article.url.split('/')[-3]
                        title = (article.title or "")[:50]
                        print(f"    - {title}... [{url_part}]")
