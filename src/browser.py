"""Browser management for web scraping."""

import atexit
import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver

from config import LOGIN_URL, PAGE_LOAD_WAIT_TIME


class BrowserManager:
  """Manages browser instance and authentication."""

  def __init__(self):
    """Initialize browser manager."""
    self.driver: Optional[WebDriver] = None
    atexit.register(self.quit)

  def setup(self) -> None:
    """Initialize Selenium Chrome driver with anti-detection options.

    Raises:
        RuntimeError: If Chrome or ChromeDriver is not installed.
    """
    print("Starting Chrome browser...")
    try:
      options = webdriver.ChromeOptions()
      options.add_argument("--disable-blink-features=AutomationControlled")
      options.add_experimental_option("excludeSwitches", ["enable-logging"])
      options.add_argument("--disable-gpu")
      options.add_argument("--no-sandbox")
      options.add_argument("--disable-dev-shm-usage")
      self.driver = webdriver.Chrome(options=options)
    except Exception as e:
      raise RuntimeError(
        f"Failed to start Chrome browser. Ensure Chrome and ChromeDriver "
        f"are installed: {e}"
      )

  def login(self) -> None:
    """Navigate to login page and wait for manual authentication."""
    if not self.driver:
      raise RuntimeError("Browser not initialized. Call setup() first.")

    print("Navigating to login page...")
    self.driver.get(LOGIN_URL)
    print("\n" + "=" * 60)
    print("Please log in to The Economist in the browser")
    print("After logging in, press Enter to continue...")
    print("=" * 60 + "\n")
    input()
    print("Login complete")

  def navigate(self, url: str, wait_time: int = PAGE_LOAD_WAIT_TIME) -> str:
    """Navigate to URL and return page source.

    Args:
        url: URL to navigate to.
        wait_time: Time to wait for page load.

    Returns:
        Page HTML source.
    """
    if not self.driver:
      raise RuntimeError("Browser not initialized. Call setup() first.")

    self.driver.get(url)
    time.sleep(wait_time)
    return self.driver.page_source

  def quit(self) -> None:
    """Close browser and cleanup."""
    if self.driver:
      try:
        self.driver.quit()
      except Exception:
        pass
      finally:
        self.driver = None
