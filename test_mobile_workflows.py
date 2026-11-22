from playwright.sync_api import Page, expect


def test_mobile_job_search_and_browsing_elements(mobile_page: Page) -> None:
	"""Verify visible mobile search, filter, and browsing containers fit the viewport."""
	mobile_page.goto("https://www.matchwise.tech/", wait_until="domcontentloaded")
	expect(mobile_page.locator(".landing-page")).to_be_visible()
	assert mobile_page.evaluate("() => window.innerWidth") == 375

	element_selector = (
		"input[type='search'], "
		"input[placeholder*='search' i], "
		"[role='search'] input, "
		"select, "
		"[role='filter'], "
		"[class*='job-card' i], "
		"[class*='listing-card' i], "
		".landing-page section, "
		".landing-page main > *"
	)
	elements = mobile_page.locator(element_selector)
	assert elements.count() > 0

	visible_elements = 0
	for index in range(elements.count()):
		element = elements.nth(index)
		if not element.is_visible():
			continue

		visible_elements += 1
		bounds = element.bounding_box()
		assert bounds is not None
		assert bounds["x"] >= 0, (
			f"Mobile browsing element starts at x={bounds['x']} and is clipped"
		)
		assert bounds["x"] + bounds["width"] <= 375, (
			f"Mobile browsing element ends at "
			f"{bounds['x'] + bounds['width']}px and exceeds the 375px viewport"
		)

	assert visible_elements > 0


def test_cross_browser_webkit_mobile_render(ios_webkit_page: Page) -> None:
	"""Verify the landing page renders cleanly in mobile Safari WebKit."""
	ios_webkit_page.goto(
		"https://www.matchwise.tech/", wait_until="domcontentloaded"
	)
	expect(ios_webkit_page.locator(".landing-page")).to_be_visible()

	assert ios_webkit_page.title().strip(), "WebKit page title should not be empty"

	inner_width = ios_webkit_page.evaluate("() => window.innerWidth")
	scroll_width = ios_webkit_page.evaluate(
		"() => document.documentElement.scrollWidth"
	)
	assert scroll_width <= inner_width, (
		f"WebKit page has horizontal overflow: "
		f"scrollWidth={scroll_width}, innerWidth={inner_width}"
	)

	cta = ios_webkit_page.get_by_role(
		"button", name="Find my matches", exact=True
	)
	if cta.count() == 0:
		cta = ios_webkit_page.get_by_role(
			"button", name="Get started", exact=True
		)

	expect(cta).to_be_visible()
	expect(cta).to_be_enabled()
	cta.click()