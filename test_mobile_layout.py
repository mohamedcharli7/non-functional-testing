import pytest
from playwright.sync_api import Page, expect


def _visit(page: Page, url: str, expected_selector: str) -> None:
	page.goto(url, wait_until="domcontentloaded")
	expect(page.locator(expected_selector)).to_be_visible()


@pytest.mark.parametrize("page_fixture", ("mobile_page", "tablet_page"))
def test_no_horizontal_overflow_mobile_and_tablet(
	request: pytest.FixtureRequest,
	page_fixture: str,
	target_urls: list[str],
) -> None:
	"""Verify every target page fits within mobile and tablet viewport widths."""
	page: Page = request.getfixturevalue(page_fixture)
	viewport_name = "mobile" if page_fixture == "mobile_page" else "tablet"

	for url in target_urls:
		expected_selector = ".landing-page" if url == target_urls[0] else ".auth-page"
		_visit(page, url, expected_selector)

		viewport_width = page.evaluate("() => window.innerWidth")
		scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
		assert scroll_width <= viewport_width, (
			f"{viewport_name} page {url} has horizontal overflow: "
			f"scrollWidth={scroll_width}, innerWidth={viewport_width}"
		)


def test_mobile_navigation_menu_adaptation(
	mobile_page: Page, target_urls: list[str]
) -> None:
	"""Verify the mobile header and primary navigation remain visible and usable."""
	_visit(mobile_page, target_urls[0], ".landing-page")

	header = mobile_page.locator("header.landing-header")
	expect(header).to_be_visible()
	header_bounds = header.bounding_box()
	assert header_bounds is not None

	viewport_width = mobile_page.evaluate("() => window.innerWidth")
	assert viewport_width == 375
	assert header_bounds["x"] >= 0
	assert header_bounds["x"] + header_bounds["width"] <= viewport_width

	log_in = header.get_by_role("link", name="Log in", exact=True)
	get_started = header.get_by_role("button", name="Get started", exact=True)
	expect(log_in).to_be_visible()
	expect(get_started).to_be_visible()
	assert log_in.is_enabled()
	assert get_started.is_enabled()


def test_mobile_register_form_vertical_stacking(
	mobile_page: Page, target_urls: list[str]
) -> None:
	"""Verify registration name fields stack vertically on the mobile viewport."""
	_visit(mobile_page, target_urls[2], ".auth-page")

	first_name = mobile_page.get_by_label("First name", exact=True)
	last_name = mobile_page.get_by_label("Last name", exact=True)
	expect(first_name).to_be_visible()
	expect(last_name).to_be_visible()

	first_bounds = first_name.bounding_box()
	last_bounds = last_name.bounding_box()
	assert first_bounds is not None
	assert last_bounds is not None

	first_bottom = first_bounds["y"] + first_bounds["height"]
	assert first_bottom <= last_bounds["y"], (
		"First name and last name inputs should stack vertically on mobile"
	)

	viewport_width = mobile_page.evaluate("() => window.innerWidth")
	assert viewport_width == 375
	for field_name, bounds in (
		("First name", first_bounds),
		("Last name", last_bounds),
	):
		assert bounds["x"] >= 0
		assert bounds["x"] + bounds["width"] <= viewport_width, (
			f"{field_name} input exceeds the 375px mobile viewport"
		)