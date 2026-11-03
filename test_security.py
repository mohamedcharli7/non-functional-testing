from urllib.parse import urlsplit

from playwright.sync_api import Page, expect
import requests


def test_https_enforcement(
	requests_session: requests.Session, target_urls: list[str]
) -> None:
	for https_url in target_urls:
		response = requests_session.get(https_url, timeout=20)
		assert urlsplit(response.url).scheme == "https", (
			f"{https_url} did not end on HTTPS (final URL: {response.url})"
		)

		http_url = https_url.replace("https://", "http://", 1)
		http_response = requests_session.get(
			http_url, allow_redirects=False, timeout=20
		)
		location = http_response.headers.get("Location", "")
		assert http_response.is_redirect and urlsplit(location).scheme == "https", (
			f"{http_url} did not redirect unencrypted traffic to HTTPS "
			f"(status: {http_response.status_code}, location: {location!r})"
		)


def test_security_headers(
	requests_session: requests.Session, target_urls: list[str]
) -> None:
	for url in target_urls:
		response = requests_session.get(url, timeout=20)
		headers = {name.lower(): value for name, value in response.headers.items()}

		assert "strict-transport-security" in headers, (
			f"{url} is missing the Strict-Transport-Security header"
		)
		assert headers.get("x-content-type-options", "").lower() == "nosniff", (
			f"{url} must set X-Content-Type-Options: nosniff"
		)


def test_password_input_masking(
	desktop_page: Page, target_urls: list[str]
) -> None:
	for url in target_urls[1:]:
		desktop_page.goto(url, wait_until="domcontentloaded")
		password_inputs = desktop_page.locator(
			'input[name="password"], input[name="confirmPassword"]'
		)
		expect(password_inputs.first).to_be_attached()
		for index in range(password_inputs.count()):
			assert password_inputs.nth(index).get_attribute("type") == "password", (
				f"Password input {index + 1} on {url} is not masked"
			)