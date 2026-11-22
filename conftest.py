"""Shared pytest fixtures for desktop browser and HTTP tests."""

from collections.abc import Iterator

import pytest
import requests
from playwright.sync_api import Page, sync_playwright

BASE_URL = "https://www.matchwise.tech"


@pytest.fixture
def desktop_page() -> Iterator[Page]:
	"""Provide a Chromium page configured for a 1440x900 desktop viewport."""
	with sync_playwright() as playwright:
		browser = playwright.chromium.launch()
		page = browser.new_page(viewport={"width": 1440, "height": 900})
		try:
			yield page
		finally:
			browser.close()


@pytest.fixture
def desktop_hd_page() -> Iterator[Page]:
	"""Provide a Chromium page configured for a 1920x1080 Full HD desktop viewport."""
	with sync_playwright() as playwright:
		browser = playwright.chromium.launch()
		page = browser.new_page(viewport={"width": 1920, "height": 1080})
		try:
			yield page
		finally:
			browser.close()


@pytest.fixture
def mobile_page() -> Iterator[Page]:
	"""Provide a Chromium page configured for an iPhone-sized mobile viewport."""
	with sync_playwright() as playwright:
		browser = playwright.chromium.launch()
		page = browser.new_page(
			viewport={"width": 375, "height": 812},
			is_mobile=True,
			has_touch=True,
		)
		try:
			yield page
		finally:
			browser.close()


@pytest.fixture
def tablet_page() -> Iterator[Page]:
	"""Provide a Chromium page configured for an iPad-sized tablet viewport."""
	with sync_playwright() as playwright:
		browser = playwright.chromium.launch()
		page = browser.new_page(
			viewport={"width": 768, "height": 1024},
			is_mobile=True,
			has_touch=True,
		)
		try:
			yield page
		finally:
			browser.close()


@pytest.fixture
def ios_webkit_page() -> Iterator[Page]:
	"""Provide a WebKit page configured for an iOS-sized mobile viewport."""
	with sync_playwright() as playwright:
		browser = playwright.webkit.launch()
		page = browser.new_page(
			viewport={"width": 390, "height": 844},
			is_mobile=True,
			has_touch=True,
		)
		try:
			yield page
		finally:
			browser.close()


@pytest.fixture
def target_urls() -> list[str]:
	"""Return the Matchwise desktop pages used by browser tests."""
	return [
		f"{BASE_URL}/",
		f"{BASE_URL}/login",
		f"{BASE_URL}/register",
	]


@pytest.fixture
def requests_session() -> Iterator[requests.Session]:
	"""Provide a reusable requests session for HTTP checks alongside desktop tests."""
	session = requests.Session()
	try:
		yield session
	finally:
		session.close()