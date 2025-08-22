"""Image handling for EPUB generation."""

import re
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urljoin

import requests
from PIL import Image, ImageDraw

from config import (
    COVER_IMAGE_HEIGHT, COVER_IMAGE_QUALITY, COVER_IMAGE_WIDTH,
    HIGH_RES_IMAGE_WIDTH, IMAGE_QUALITY, IMAGE_QUALITY_STANDARD,
    USER_AGENT
)


class ImageHandler:
    """Handles image downloading and processing for EPUB."""

    def __init__(self, debug: bool = False):
        """Initialize image handler.

        Args:
            debug: Enable debug output.
        """
        self.debug = debug
        self.images_added = 0
        self.seen_urls = set()

    def download_image(self, img_url: str) -> Optional[bytes]:
        """Download and process image for EPUB.

        Args:
            img_url: URL of image to download.

        Returns:
            Processed image data or None if failed.
        """
        if not img_url or not isinstance(img_url, str):
            return None

        # Validate URL to prevent SSRF
        if any(pattern in img_url.lower() for pattern in
               ['javascript:', 'data:', 'vbscript:', 'file:', 'ftp:']):
            return None

        try:
            original_url = img_url
            img_url = self._get_highest_resolution_url(img_url)

            if not img_url.startswith('http'):
                img_url = urljoin('https://www.economist.com', img_url)

            self.seen_urls.add(original_url)
            self.seen_urls.add(img_url)

            # Download image with size limit
            response = requests.get(
                img_url,
                timeout=10,
                headers={'User-Agent': USER_AGENT},
                stream=True
            )

            # Check content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                if self.debug:
                    print(f"    Skipped non-image content type: {content_type}")
                return None

            # Limit download size to 10MB
            max_size = 10 * 1024 * 1024
            img_data = b''
            for chunk in response.iter_content(chunk_size=8192):
                img_data += chunk
                if len(img_data) > max_size:
                    if self.debug:
                        print("    Image too large (>10MB), skipping")
                    return None

            if self.debug:
                filename = img_url.split('/')[-1][:40]
                print(f"    Downloaded {len(img_data)} bytes from "
                      f"{filename}...")

            # Process with PIL
            img = Image.open(BytesIO(img_data))

            if self.debug:
                print(f"    Image dimensions: {img.width}x{img.height}")
                self._save_debug_image(img_data)

            # Convert to RGB JPEG for compatibility
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')

            # Save as JPEG
            output = BytesIO()
            img.save(output, format='JPEG', quality=IMAGE_QUALITY,
                     optimize=False)

            self.images_added += 1
            return output.getvalue()

        except Exception as e:
            if self.debug:
                print(f"    Failed to download image: {e}")
            return None

    def download_cover(self, cover_url: str) -> Tuple[bytes, bytes]:
        """Download and process cover image.

        Args:
            cover_url: Cover image URL.

        Returns:
            Tuple of (metadata_cover_data, full_resolution_cover_data).

        Raises:
            Exception: If cover download fails.
        """
        if not cover_url or not isinstance(cover_url, str):
            raise ValueError("Invalid cover URL")

        if not cover_url.startswith('http'):
            cover_url = urljoin('https://www.economist.com', cover_url)

        response = requests.get(
            cover_url,
            timeout=10,
            headers={'User-Agent': USER_AGENT}
        )
        response.raise_for_status()

        # Validate content type
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            raise ValueError(f"Invalid content type for cover: {content_type}")

        img_data = response.content

        # Process for full resolution
        img_original = Image.open(BytesIO(img_data))
        if img_original.mode != 'RGB':
            img_original = img_original.convert('RGB')

        # Save full resolution
        full_output = BytesIO()
        img_original.save(full_output, format='JPEG',
                          quality=COVER_IMAGE_QUALITY, optimize=False)
        full_res_data = full_output.getvalue()

        # Create resized version for metadata
        img = img_original.copy()
        if img.width > COVER_IMAGE_WIDTH:
            ratio = COVER_IMAGE_WIDTH / img.width
            new_height = int(img.height * ratio)
            img = img.resize((COVER_IMAGE_WIDTH, new_height),
                             Image.Resampling.LANCZOS)

        output = BytesIO()
        img.save(output, format='JPEG', quality=90)
        cover_data = output.getvalue()

        return cover_data, full_res_data

    def create_default_cover(self) -> bytes:
        """Create a default cover image.

        Returns:
            Cover image data as bytes.
        """
        img = Image.new('RGB', (COVER_IMAGE_WIDTH, COVER_IMAGE_HEIGHT),
                        '#E3120B')
        ImageDraw.Draw(img)  # Future use for text overlay

        output = BytesIO()
        img.save(output, format='JPEG', quality=90)
        return output.getvalue()

    def _get_highest_resolution_url(self, img_url: str) -> str:
        """Get highest resolution version of image URL.

        Args:
            img_url: Original image URL.

        Returns:
            Highest resolution URL available.
        """
        if 'cdn-cgi/image' in img_url:
            match = re.search(r'/content-assets/.*?\.(jpg|jpeg|png)',
                              img_url)
            if match:
                base_path = match.group(0)
                high_res = (
                    f'https://www.economist.com/cdn-cgi/image/'
                    f'width={HIGH_RES_IMAGE_WIDTH},'
                    f'quality={IMAGE_QUALITY_STANDARD},'
                    f'format=auto{base_path}'
                )
                if self.debug:
                    print(f"    Upgraded to high-res: {high_res}")
                return high_res

        return img_url

    def _save_debug_image(self, img_data: bytes) -> None:
        """Save image to debug directory.

        Args:
            img_data: Raw image data.
        """
        debug_dir = Path('debug/images')
        debug_dir.mkdir(exist_ok=True, parents=True)
        filename = debug_dir / f'image_{self.images_added:03d}_original.jpg'
        with open(filename, 'wb') as f:
            f.write(img_data)
        print(f"    Debug image saved: {filename}")
