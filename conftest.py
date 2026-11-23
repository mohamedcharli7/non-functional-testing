"""Shared pytest fixtures for desktop browser and HTTP tests."""

import os
from collections.abc import Iterator
from pathlib import Path

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


@pytest.fixture(scope="session")
def auth_state_path() -> str:
	"""Log in once and return the path to the saved authenticated browser state."""
	email = os.getenv("MATCHWISE_EMAIL")
	password = os.getenv("MATCHWISE_PASSWORD")
	if not email or not password:
		pytest.skip("MATCHWISE_EMAIL and MATCHWISE_PASSWORD must be set for authenticated tests")

	with sync_playwright() as playwright:
		browser = playwright.chromium.launch(headless=True)
		try:
			context = browser.new_context()
			page = context.new_page()
			response = page.goto(
				f"{BASE_URL}/login", wait_until="domcontentloaded"
			)
			email_input = page.locator(
				'input[type="email"], input[name="email"]'
			).first
			password_input = page.locator(
				'input[type="password"], input[name="password"]'
			).first
			if (
				(response is not None and response.status == 404)
				or email_input.count() == 0
				or password_input.count() == 0
			):
				page.goto(BASE_URL, wait_until="domcontentloaded")
				login_link = page.get_by_role(
					"link", name="Log in", exact=True
				).first
				login_button = page.get_by_role(
					"button", name="Log in", exact=True
				).first
				if login_link.count() > 0 and login_link.is_visible():
					login_link.click()
				elif login_button.count() > 0 and login_button.is_visible():
					login_button.click()
				else:
					raise AssertionError(
						"Could not find a visible Log in link or button on the home page"
					)

				email_input = page.locator(
					'input[type="email"], input[name="email"]'
				).first
				password_input = page.locator(
					'input[type="password"], input[name="password"]'
				).first

			email_input.fill(email)
			password_input.fill(password)
			page.locator('button[type="submit"]').first.click()
			page.get_by_text("Log out").wait_for(
				state="visible", timeout=15000
			)
			page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
			context.storage_state(path="auth.json")
			Path("session_auth.json").write_text(
				page.evaluate("() => JSON.stringify(sessionStorage)"),
				encoding="utf-8",
			)
			return "auth.json"
		finally:
			browser.close()


@pytest.fixture
def authenticated_desktop_page(auth_state_path: str) -> Iterator[Page]:
	"""Provide an authenticated Chromium page configured for a 1440x900 desktop viewport."""
	with sync_playwright() as playwright:
		browser = playwright.chromium.launch()
		try:
			context = browser.new_context(
				viewport={"width": 1440, "height": 900},
				storage_state=auth_state_path,
			)
			session_auth_path = Path("session_auth.json")
			if session_auth_path.exists():
				session_json = session_auth_path.read_text(encoding="utf-8")
				context.add_init_script(
					f"""
					const data = {session_json};
					for (const [k, v] of Object.entries(data)) {{
						window.sessionStorage.setItem(k, v);
					}}
					"""
				)
			page = context.new_page()
			yield page
		finally:
			browser.close()


@pytest.fixture
def authenticated_mobile_page(auth_state_path: str) -> Iterator[Page]:
	"""Provide an authenticated Chromium page configured for an iPhone-sized mobile viewport."""
	with sync_playwright() as playwright:
		browser = playwright.chromium.launch()
		try:
			context = browser.new_context(
				viewport={"width": 375, "height": 812},
				is_mobile=True,
				has_touch=True,
				storage_state=auth_state_path,
			)
			session_auth_path = Path("session_auth.json")
			if session_auth_path.exists():
				session_json = session_auth_path.read_text(encoding="utf-8")
				context.add_init_script(
					f"""
					const data = {session_json};
					for (const [k, v] of Object.entries(data)) {{
						window.sessionStorage.setItem(k, v);
					}}
					"""
				)
			page = context.new_page()
			yield page
		finally:
			browser.close()