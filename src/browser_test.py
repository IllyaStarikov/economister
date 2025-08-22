"""Tests for the browser module."""

import unittest
from unittest.mock import Mock, patch
from browser import BrowserManager


class TestBrowserManager(unittest.TestCase):
  """Test BrowserManager class."""

  def setUp(self):
    """Set up test fixtures."""
    self.browser = BrowserManager()

  def tearDown(self):
    """Clean up after tests."""
    # Ensure driver is quit if it exists
    if self.browser.driver:
      try:
        self.browser.driver.quit()
      except:
        pass

  @patch("browser.webdriver.Chrome")
  def test_setup_success(self, mock_chrome):
    """Test successful browser setup."""
    mock_driver = Mock()
    mock_chrome.return_value = mock_driver

    self.browser.setup()

    mock_chrome.assert_called_once()
    self.assertEqual(self.browser.driver, mock_driver)

    # Check Chrome options were set
    call_args = mock_chrome.call_args
    options = call_args[1]["options"]
    self.assertIsNotNone(options)

  @patch("browser.webdriver.Chrome")
  def test_setup_failure(self, mock_chrome):
    """Test browser setup failure."""
    mock_chrome.side_effect = Exception("ChromeDriver not found")

    with self.assertRaises(RuntimeError) as context:
      self.browser.setup()

    self.assertIn("Failed to start Chrome browser", str(context.exception))
    self.assertIn("ChromeDriver not found", str(context.exception))

  @patch("browser.input", return_value="")
  @patch("browser.webdriver.Chrome")
  def test_login(self, mock_chrome, mock_input):
    """Test login flow."""
    mock_driver = Mock()
    mock_chrome.return_value = mock_driver

    self.browser.setup()
    self.browser.login()

    mock_driver.get.assert_called_once_with(
      "https://www.economist.com/api/auth/login"
    )
    mock_input.assert_called_once()

  def test_login_without_setup(self):
    """Test login without browser setup."""
    with self.assertRaises(RuntimeError) as context:
      self.browser.login()

    self.assertIn("Browser not initialized", str(context.exception))

  @patch("browser.time.sleep")
  @patch("browser.webdriver.Chrome")
  def test_navigate(self, mock_chrome, mock_sleep):
    """Test page navigation."""
    mock_driver = Mock()
    mock_driver.page_source = "<html>Test Page</html>"
    mock_chrome.return_value = mock_driver

    self.browser.setup()
    result = self.browser.navigate("https://example.com/page")

    mock_driver.get.assert_called_with("https://example.com/page")
    mock_sleep.assert_called_once_with(5)  # Default wait time
    self.assertEqual(result, "<html>Test Page</html>")

  @patch("browser.time.sleep")
  @patch("browser.webdriver.Chrome")
  def test_navigate_custom_wait(self, mock_chrome, mock_sleep):
    """Test navigation with custom wait time."""
    mock_driver = Mock()
    mock_driver.page_source = "<html>Test</html>"
    mock_chrome.return_value = mock_driver

    self.browser.setup()
    self.browser.navigate("https://example.com", wait_time=10)

    mock_sleep.assert_called_once_with(10)

  def test_navigate_without_setup(self):
    """Test navigation without browser setup."""
    with self.assertRaises(RuntimeError) as context:
      self.browser.navigate("https://example.com")

    self.assertIn("Browser not initialized", str(context.exception))

  @patch("browser.webdriver.Chrome")
  def test_quit(self, mock_chrome):
    """Test browser cleanup."""
    mock_driver = Mock()
    mock_chrome.return_value = mock_driver

    self.browser.setup()
    self.assertIsNotNone(self.browser.driver)

    self.browser.quit()

    mock_driver.quit.assert_called_once()
    self.assertIsNone(self.browser.driver)

  @patch("browser.webdriver.Chrome")
  def test_quit_with_error(self, mock_chrome):
    """Test browser cleanup with error."""
    mock_driver = Mock()
    mock_driver.quit.side_effect = Exception("Browser already closed")
    mock_chrome.return_value = mock_driver

    self.browser.setup()
    self.browser.quit()  # Should not raise exception

    self.assertIsNone(self.browser.driver)

  def test_quit_without_driver(self):
    """Test quit when no driver exists."""
    self.browser.quit()  # Should not raise exception
    self.assertIsNone(self.browser.driver)

  @patch("browser.atexit.register")
  def test_atexit_registration(self, mock_register):
    """Test that quit is registered with atexit."""
    browser = BrowserManager()
    mock_register.assert_called_once_with(browser.quit)


if __name__ == "__main__":
  unittest.main()
