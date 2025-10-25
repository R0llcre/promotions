"""Behave environment hooks for UI BDD.

This module starts a headless Chrome/Chromium browser before tests and
shuts it down afterwards. It is robust in DevContainers on Debian/Ubuntu:

Priority of driver resolution:
  1) Local chromedriver from system packages (chromium-driver)
  2) Selenium Manager (Selenium 4.10+)
  3) webdriver-manager (when USE_WDM=1)

Browser binary detection honors CHROME_BIN and common Linux paths.

BASE_URL is taken in this order:
  1) env:      BASE_URL
  2) behave:   -D BASE_URL=...
  3) default:  http://localhost:8080
"""

from __future__ import annotations

import os
import shutil
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

# Optional fallback to webdriver-manager if explicitly requested
USE_WDM = os.getenv("USE_WDM") == "1"


def _detect_chrome_binary() -> Optional[str]:
    """Return a likely Chrome/Chromium binary path or None."""
    env_bin = os.getenv("CHROME_BIN")
    if env_bin and os.path.exists(env_bin):
        return env_bin

    # Common paths in DevContainers (Debian/Ubuntu)
    for cand in ("/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"):
        if os.path.exists(cand):
            return cand

    # Try PATH lookups
    for name in ("chromium", "chromium-browser", "google-chrome", "chrome"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _detect_chromedriver() -> Optional[str]:
    """Return a likely chromedriver path from system packages or PATH."""
    env_drv = os.getenv("CHROMEDRIVER")
    if env_drv and os.path.exists(env_drv):
        return env_drv

    # Debian/Ubuntu common install locations
    for cand in ("/usr/bin/chromedriver", "/usr/lib/chromium/chromedriver"):
        if os.path.exists(cand):
            return cand

    # Try PATH
    which = shutil.which("chromedriver")
    return which


def before_all(context):
    """Start a headless browser and remember the base URL."""
    # Resolve BASE_URL
    context.base_url = (
        os.getenv("BASE_URL")
        or context.config.userdata.get("BASE_URL")
        or "http://localhost:8080"
    )

    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    chrome_bin = _detect_chrome_binary()
    if chrome_bin:
        options.binary_location = chrome_bin

    # Resolution priority: local driver -> Selenium Manager -> webdriver-manager
    driver_path = _detect_chromedriver()

    try:
        if driver_path:
            # 1) Use local chromedriver from system packages (recommended)
            from selenium.webdriver.chrome.service import Service as ChromeService

            service = ChromeService(executable_path=driver_path)
            context.browser = webdriver.Chrome(service=service, options=options)

        elif not USE_WDM:
            # 2) Use Selenium Manager (no explicit service)
            #    This will try to fetch a compatible driver automatically.
            context.browser = webdriver.Chrome(options=options)

        else:
            # 3) Explicitly use webdriver-manager (when requested)
            from selenium.webdriver.chrome.service import Service as ChromeService
            from webdriver_manager.chrome import ChromeDriverManager

            service = ChromeService(ChromeDriverManager().install())
            context.browser = webdriver.Chrome(service=service, options=options)

        context.browser.set_window_size(1400, 1000)

    except Exception as exc:  # pragma: no cover  (helpful runtime messaging)
        tips = [
            "Cannot start Chrome/Chromium in headless mode. Common fixes:",
            "  1) Install OS packages (recommended in DevContainers):",
            "       sudo apt-get update && sudo apt-get install -y chromium chromium-driver fonts-liberation",
            "  2) If Chromium is at a non-standard path, set:",
            "       export CHROME_BIN=/usr/bin/chromium",
            "     If chromedriver is at a non-standard path, set:",
            "       export CHROMEDRIVER=/usr/bin/chromedriver",
            "  3) If corporate network blocks Selenium Manager downloads, try:",
            "       USE_WDM=1 behave",
            "",
            f"Original error: {type(exc).__name__}: {exc}",
        ]
        raise RuntimeError("\n".join(tips)) from exc


def after_all(context):
    """Shut down the browser if it was started."""
    browser = getattr(context, "browser", None)
    if browser:
        browser.quit()
