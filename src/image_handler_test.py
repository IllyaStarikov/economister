"""Tests for the image_handler module."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
from PIL import Image
from image_handler import ImageHandler


class TestImageHandler(unittest.TestCase):
    """Test ImageHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = ImageHandler(debug=False)

        # Create a mock image
        self.mock_image = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        self.mock_image.save(img_bytes, format='JPEG')
        self.mock_image_data = img_bytes.getvalue()

    @patch('image_handler.requests.get')
    def test_download_image_success(self, mock_get):
        """Test successful image download."""
        # Mock response
        mock_response = Mock()
        mock_response.headers = {'content-type': 'image/jpeg'}
        mock_response.iter_content = Mock(return_value=[self.mock_image_data])
        mock_get.return_value = mock_response

        result = self.handler.download_image("https://example.com/image.jpg")

        self.assertIsNotNone(result)
        self.assertEqual(self.handler.images_added, 1)
        self.assertIn("https://example.com/image.jpg", self.handler.seen_urls)

    @patch('image_handler.requests.get')
    def test_download_image_invalid_content_type(self, mock_get):
        """Test image download with invalid content type."""
        mock_response = Mock()
        mock_response.headers = {'content-type': 'text/html'}
        mock_get.return_value = mock_response

        result = self.handler.download_image("https://example.com/page.html")

        self.assertIsNone(result)
        self.assertEqual(self.handler.images_added, 0)

    def test_download_image_invalid_url(self):
        """Test image download with invalid URLs."""
        # Malicious URLs
        self.assertIsNone(self.handler.download_image("javascript:alert('xss')"))
        self.assertIsNone(self.handler.download_image("data:text/html,<script>"))
        self.assertIsNone(self.handler.download_image("file:///etc/passwd"))

        # None or empty
        self.assertIsNone(self.handler.download_image(None))
        self.assertIsNone(self.handler.download_image(""))

    @patch('image_handler.requests.get')
    def test_download_image_size_limit(self, mock_get):
        """Test image size limit enforcement."""
        # Create large fake data
        large_data = b'x' * (11 * 1024 * 1024)  # 11MB

        mock_response = Mock()
        mock_response.headers = {'content-type': 'image/jpeg'}
        mock_response.iter_content = Mock(return_value=[large_data[:8192], large_data[8192:]])
        mock_get.return_value = mock_response

        result = self.handler.download_image("https://example.com/huge.jpg")

        self.assertIsNone(result)

    @patch('image_handler.requests.get')
    def test_download_cover_success(self, mock_get):
        """Test successful cover image download."""
        mock_response = Mock()
        mock_response.headers = {'content-type': 'image/jpeg'}
        mock_response.content = self.mock_image_data
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        metadata_cover, full_res_cover = self.handler.download_cover(
            "https://example.com/cover.jpg"
        )

        self.assertIsNotNone(metadata_cover)
        self.assertIsNotNone(full_res_cover)
        mock_response.raise_for_status.assert_called_once()

    @patch('image_handler.requests.get')
    def test_download_cover_invalid_content_type(self, mock_get):
        """Test cover download with invalid content type."""
        mock_response = Mock()
        mock_response.headers = {'content-type': 'text/html'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            self.handler.download_cover("https://example.com/page.html")

        self.assertIn("Invalid content type", str(context.exception))

    def test_download_cover_invalid_url(self):
        """Test cover download with invalid URL."""
        with self.assertRaises(ValueError) as context:
            self.handler.download_cover(None)

        self.assertIn("Invalid cover URL", str(context.exception))

    def test_create_default_cover(self):
        """Test default cover creation."""
        cover_data = self.handler.create_default_cover()

        self.assertIsNotNone(cover_data)
        self.assertIsInstance(cover_data, bytes)

        # Verify it's a valid JPEG
        img = Image.open(BytesIO(cover_data))
        self.assertEqual(img.format, 'JPEG')
        self.assertEqual(img.mode, 'RGB')

    def test_get_highest_resolution_url(self):
        """Test URL resolution upgrade."""
        # CDN URL that should be upgraded
        cdn_url = "https://www.economist.com/cdn-cgi/image/width=640,quality=70,format=auto/content-assets/image.jpg"
        result = self.handler._get_highest_resolution_url(cdn_url)

        self.assertIn("width=1424", result)
        self.assertIn("quality=80", result)

        # Regular URL should remain unchanged
        regular_url = "https://example.com/image.jpg"
        result = self.handler._get_highest_resolution_url(regular_url)
        self.assertEqual(result, regular_url)

    @patch('image_handler.requests.get')
    def test_image_format_conversion(self, mock_get):
        """Test image format conversion to RGB JPEG."""
        # Create RGBA PNG image
        rgba_image = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        img_bytes = BytesIO()
        rgba_image.save(img_bytes, format='PNG')

        mock_response = Mock()
        mock_response.headers = {'content-type': 'image/png'}
        mock_response.iter_content = Mock(return_value=[img_bytes.getvalue()])
        mock_get.return_value = mock_response

        result = self.handler.download_image("https://example.com/image.png")

        self.assertIsNotNone(result)

        # Verify output is JPEG
        output_img = Image.open(BytesIO(result))
        self.assertEqual(output_img.format, 'JPEG')
        self.assertEqual(output_img.mode, 'RGB')

    @patch('image_handler.Path.mkdir')
    @patch('builtins.open', create=True)
    def test_save_debug_image(self, mock_open, mock_mkdir):
        """Test debug image saving."""
        self.handler.debug = True
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        self.handler._save_debug_image(b'test_data')

        mock_mkdir.assert_called_once()
        mock_open.assert_called_once()
        mock_file.write.assert_called_once_with(b'test_data')


if __name__ == '__main__':
    unittest.main()
