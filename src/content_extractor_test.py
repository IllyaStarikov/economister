"""Tests for the content_extractor module."""

import unittest
from content_extractor import ContentExtractor
from test_fixtures import (
    MOCK_ARTICLE_JOBS_HTML,
    MOCK_ARTICLE_QUAKE_HTML,
    MOCK_ARTICLE_LOREM_HTML,
    MOCK_ARTICLE_EDGE_CASES_HTML,
    MOCK_WEEKLY_EDITION_HTML
)


class TestContentExtractor(unittest.TestCase):
    """Test ContentExtractor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.extractor = ContentExtractor(debug=False)

    def test_extract_article_jobs(self):
        """Test extracting Steve Jobs themed article."""
        article = self.extractor.extract_article(
            MOCK_ARTICLE_JOBS_HTML,
            url="https://example.com/article"
        )

        # Check title and subtitle
        self.assertEqual(article.title, "Stay Hungry, Stay Foolish: The Stanford Legacy")
        self.assertEqual(article.subtitle, "How three stories shaped a generation of entrepreneurs")

        # Check paragraphs
        self.assertEqual(article.paragraph_count, 4)

        # Check first paragraph contains expected text
        first_para = article.content_blocks[1].content  # First is hero image
        self.assertIn("connect the dots", first_para)
        self.assertIn("Lorem ipsum", first_para)

        # Check image extraction
        self.assertGreater(article.image_count, 0)

        # Check for figure with caption
        has_captioned_image = False
        for block in article.content_blocks:
            if block.type == 'image' and block.image:
                if block.image.caption and "dots metaphor" in block.image.caption:
                    has_captioned_image = True
                    self.assertEqual(block.image.credit, "Illustration: Lorem Ipsum Studios")
        self.assertTrue(has_captioned_image)

    def test_extract_article_quake(self):
        """Test extracting Quake/fast inverse sqrt article."""
        article = self.extractor.extract_article(MOCK_ARTICLE_QUAKE_HTML)

        self.assertEqual(article.title, "The magic of 0x5f3759df: A computational miracle")
        self.assertEqual(article.subtitle, "How a mysterious constant revolutionized 3D graphics")

        # Check for code mention
        has_magic_constant = False
        for block in article.content_blocks:
            if block.type == 'paragraph' and block.content:
                if "0x5f3759df" in block.content:
                    has_magic_constant = True
        self.assertTrue(has_magic_constant)

        # Check images with captions
        image_count = 0
        for block in article.content_blocks:
            if block.type == 'image' and block.image:
                image_count += 1
                if block.image.caption:
                    self.assertIsNotNone(block.image.caption)
        self.assertGreater(image_count, 0)

    def test_extract_article_lorem(self):
        """Test extracting lorem ipsum article."""
        article = self.extractor.extract_article(MOCK_ARTICLE_LOREM_HTML)

        self.assertEqual(article.title, "Lorem Ipsum: A Deep Dive into Placeholder Text")

        # Check paragraph extraction
        self.assertGreaterEqual(article.paragraph_count, 3)

        # Check Lorem content
        has_lorem = False
        for block in article.content_blocks:
            if block.type == 'paragraph' and block.content:
                if "Lorem ipsum dolor sit amet" in block.content:
                    has_lorem = True
        self.assertTrue(has_lorem)

    def test_extract_article_edge_cases(self):
        """Test edge cases and filtering."""
        article = self.extractor.extract_article(MOCK_ARTICLE_EDGE_CASES_HTML)

        # Title with HTML tags
        self.assertEqual(article.title, "Testing Edge Cases")

        # Short paragraph should be filtered
        paragraphs = [b for b in article.content_blocks if b.type == 'paragraph']
        for p in paragraphs:
            self.assertGreater(len(p.content), 20)  # MIN_PARAGRAPH_LENGTH

        # Newsletter/subscribe content should be filtered
        for block in article.content_blocks:
            if block.type == 'paragraph':
                self.assertNotIn("newsletter", block.content.lower())
                self.assertNotIn("subscribe", block.content.lower())

        # XSS and tracking images should be filtered
        image_blocks = [b for b in article.content_blocks if b.type == 'image']
        # All malicious images should have been filtered out
        for block in image_blocks:
            if block.image:
                self.assertNotIn("javascript:", block.image.src)
                self.assertNotIn("tracking.gif", block.image.src)
                self.assertNotIn("_DE_", block.image.src)  # Cover image filtered

        # Symbol conversion
        has_symbols = False
        for block in article.content_blocks:
            if block.type == 'paragraph' and block.content:
                if "™" in block.content or "®" in block.content or "©" in block.content:
                    has_symbols = True
        self.assertTrue(has_symbols)

    def test_extract_cover_url(self):
        """Test extracting cover image URL."""
        # With cover image
        cover_url = self.extractor.extract_cover_url(MOCK_WEEKLY_EDITION_HTML)
        self.assertIsNotNone(cover_url)
        self.assertIn("_DE_", cover_url)

        # Without cover image
        cover_url = self.extractor.extract_cover_url("<html><body>No images</body></html>")
        self.assertIsNone(cover_url)

    def test_extract_article_links(self):
        """Test extracting article links from weekly edition."""
        links = self.extractor.extract_article_links(MOCK_WEEKLY_EDITION_HTML)

        # Should find all article links
        self.assertGreater(len(links), 0)

        # Check structure
        for link in links:
            self.assertIn('title', link)
            self.assertIn('url', link)
            self.assertIn('section', link)

            # URL should be absolute
            self.assertTrue(link['url'].startswith('https://'))

            # Should have detected section
            self.assertIsNotNone(link['section'])

        # Check specific articles
        titles = [link['title'] for link in links]
        self.assertIn("Stay Hungry, Stay Foolish: The Stanford Legacy", titles)
        self.assertIn("The magic of 0x5f3759df: A computational miracle", titles)

    def test_hero_image_extraction(self):
        """Test hero image extraction."""
        # Reset seen URLs for clean test
        self.extractor.seen_image_urls = set()

        article = self.extractor.extract_article(MOCK_ARTICLE_JOBS_HTML)

        # Should have hero image as first image
        first_image = None
        for block in article.content_blocks:
            if block.type == 'image':
                first_image = block.image
                break

        self.assertIsNotNone(first_image)
        self.assertTrue(first_image.is_hero)

    def test_caption_credit_extraction(self):
        """Test extraction of image captions and credits."""
        article = self.extractor.extract_article(MOCK_ARTICLE_QUAKE_HTML)

        # Find images with captions and credits
        found_photo_credit = False
        found_chart_credit = False

        for block in article.content_blocks:
            if block.type == 'image' and block.image:
                if block.image.credit:
                    if "Photo:" in block.image.credit:
                        found_photo_credit = True
                    elif "Chart:" in block.image.credit:
                        found_chart_credit = True

        self.assertTrue(found_photo_credit)
        self.assertTrue(found_chart_credit)


if __name__ == '__main__':
    unittest.main()
