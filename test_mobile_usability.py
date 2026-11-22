from playwright.sync_api import Page, expect


def _visit(page: Page, url: str, expected_selector: str) -> None:
	page.goto(url, wait_until="domcontentloaded")
	expect(page.locator(expected_selector)).to_be_visible()


def test_mobile_touch_target_sizes(
	mobile_page: Page, target_urls: list[str]
) -> None:
	"""Verify primary actions and form fields provide reliable touch target sizes."""
	_visit(mobile_page, target_urls[0], ".landing-page")
	assert mobile_page.evaluate("() => window.innerWidth") == 375
	for action_name in ("Find my matches", "Get started"):
		action = mobile_page.get_by_role("button", name=action_name, exact=True)
		expect(action).to_be_visible()
		action_bounds = action.bounding_box()
		assert action_bounds is not None
		assert action_bounds["height"] >= 40, (
			f"{action_name} touch target is only {action_bounds['height']}px high"
		)
		assert action_bounds["width"] >= 44, (
			f"{action_name} touch target is only {action_bounds['width']}px wide"
		)

	_visit(mobile_page, target_urls[2], ".auth-page")
	create_account = mobile_page.get_by_role(
		"button", name="Create account", exact=True
	)
	expect(create_account).to_be_visible()
	create_account_bounds = create_account.bounding_box()
	assert create_account_bounds is not None
	assert create_account_bounds["height"] >= 40
	assert create_account_bounds["width"] >= 44

	form_inputs = mobile_page.locator("input:not([type='checkbox'])")
	assert form_inputs.count() > 0
	for index in range(form_inputs.count()):
		field = form_inputs.nth(index)
		expect(field).to_be_visible()
		field_bounds = field.bounding_box()
		assert field_bounds is not None
		field_name = field.get_attribute("name") or f"input {index + 1}"
		assert field_bounds["height"] >= 40, (
			f"{field_name} touch target is only {field_bounds['height']}px high"
		)
		assert field_bounds["width"] >= 44, (
			f"{field_name} touch target is only {field_bounds['width']}px wide"
		)


def test_mobile_text_readability_font_size(
	mobile_page: Page, target_urls: list[str]
) -> None:
	"""Verify primary descriptions and form labels remain at least 13px on mobile."""
	for url in target_urls:
		expected_selector = ".landing-page" if url == target_urls[0] else ".auth-page"
		_visit(mobile_page, url, expected_selector)

		paragraphs = mobile_page.locator("p")
		for index in range(paragraphs.count()):
			paragraph = paragraphs.nth(index)
			if not paragraph.is_visible():
				continue
			font_size = paragraph.evaluate(
				"(element) => parseFloat(getComputedStyle(element).fontSize)"
			)
			assert font_size >= 13, (
				f"Paragraph on {url} renders at {font_size}px, below 13px"
			)

		labels = mobile_page.locator("label")
		for index in range(labels.count()):
			label = labels.nth(index)
			if not label.is_visible():
				continue
			label_text = label.inner_text().strip()
			if label_text.startswith("I agree"):
				continue
			font_size = label.evaluate(
				"(element) => parseFloat(getComputedStyle(element).fontSize)"
			)
			assert font_size >= 13, (
				f"Form label {label_text!r} on {url} renders at "
				f"{font_size}px, below 13px"
			)


def test_mobile_validation_error_no_overlap(
	mobile_page: Page, target_urls: list[str]
) -> None:
	"""Verify the password error does not overlap its helper text on mobile."""
	_visit(mobile_page, target_urls[2], ".auth-page")

	create_account = mobile_page.get_by_role(
		"button", name="Create account", exact=True
	)
	create_account.click()

	error_text = mobile_page.get_by_text("Password is required", exact=True)
	helper_text = mobile_page.get_by_text("Use 8+ characters", exact=False)
	expect(error_text).to_be_visible()
	expect(helper_text).to_be_visible()

	error_bounds = error_text.bounding_box()
	helper_bounds = helper_text.bounding_box()
	assert error_bounds is not None
	assert helper_bounds is not None

	error_bottom = error_bounds["y"] + error_bounds["height"]
	assert error_bottom <= helper_bounds["y"], (
		"Password validation error overlaps the password helper text"
	)