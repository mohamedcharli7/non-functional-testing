from playwright.sync_api import Page, expect


def _visit(page: Page, url: str, expected_selector: str) -> None:
	page.goto(url, wait_until="domcontentloaded")
	expect(page.locator(expected_selector)).to_be_visible()


def test_desktop_header_navigation(desktop_page: Page, target_urls: list[str]) -> None:
	_visit(desktop_page, target_urls[0], ".landing-page")
	header = desktop_page.locator("header.landing-header")

	for link_name in ("Features", "Why Matchwise"):
		expect(header.get_by_role("link", name=link_name, exact=True)).to_be_visible()

	expect(header.get_by_role("link", name="Log in", exact=True)).to_be_visible()
	expect(header.get_by_role("button", name="Get started", exact=True)).to_be_visible()


def test_split_screen_desktop_layout(desktop_page: Page, target_urls: list[str]) -> None:
	viewport_width = desktop_page.evaluate("() => window.innerWidth")

	for url in target_urls[1:]:
		_visit(desktop_page, url, ".auth-page")
		left_panel = desktop_page.locator(".auth-left-panel")
		right_panel = desktop_page.locator(".auth-right-panel")
		expect(left_panel).to_be_visible()
		expect(right_panel).to_be_visible()

		left_bounds = left_panel.bounding_box()
		right_bounds = right_panel.bounding_box()
		assert left_bounds is not None
		assert right_bounds is not None

		assert abs(left_bounds["x"]) <= 1, f"{url} branding panel should start at the viewport edge"
		assert abs(right_bounds["x"] - (left_bounds["x"] + left_bounds["width"])) <= 1, (
			f"{url} panels should be side-by-side without a gap or overlap"
		)
		assert abs(left_bounds["width"] / viewport_width - 0.5) <= 0.02, (
			f"{url} branding panel should occupy half of the desktop viewport"
		)
		assert abs(right_bounds["width"] / viewport_width - 0.5) <= 0.02, (
			f"{url} form panel should occupy half of the desktop viewport"
		)


def test_login_left_panel_remains_visible_when_window_is_narrowed(
	desktop_page: Page, target_urls: list[str]
) -> None:
	_visit(desktop_page, target_urls[1], ".auth-page")
	desktop_page.set_viewport_size({"width": 1024, "height": 768})

	left_panel = desktop_page.locator(".auth-left-panel")
	expect(left_panel).to_be_visible()
	left_bounds = left_panel.bounding_box()
	assert left_bounds is not None

	assert left_bounds["x"] >= 0, "Login branding panel should not be clipped off the left edge"
	assert left_bounds["x"] + left_bounds["width"] <= 1024, (
		"Login branding panel should remain within the narrowed viewport"
	)


def test_register_side_by_side_inputs(
	desktop_page: Page, target_urls: list[str]
) -> None:
	_visit(desktop_page, target_urls[2], ".auth-page")
	first_name = desktop_page.get_by_label("First name", exact=True)
	last_name = desktop_page.get_by_label("Last name", exact=True)
	expect(first_name).to_be_visible()
	expect(last_name).to_be_visible()

	first_bounds = first_name.bounding_box()
	last_bounds = last_name.bounding_box()
	assert first_bounds is not None
	assert last_bounds is not None

	assert abs(first_bounds["y"] - last_bounds["y"]) <= 1, (
		"First Name and Last Name inputs should be on the same row"
	)
	assert first_bounds["x"] < last_bounds["x"], (
		"First Name should appear to the left of Last Name"
	)


def test_cta_hover_cursor_states(
	desktop_page: Page, target_urls: list[str]
) -> None:
	cta_names = ("Find my matches", "Log in", "Create account")

	for url, cta_name in zip(target_urls, cta_names, strict=True):
		expected_selector = ".landing-page" if url == target_urls[0] else ".auth-page"
		_visit(desktop_page, url, expected_selector)
		cta = desktop_page.get_by_role("button", name=cta_name, exact=True)
		expect(cta).to_be_visible()
		cta.hover()

		cursor = cta.evaluate("(element) => getComputedStyle(element).cursor")
		assert cursor == "pointer", (
			f"{cta_name!r} on {url} should use the pointer cursor, got {cursor!r}"
		)

def test_password_error_text_no_overlap(desktop_page: Page, target_urls: list[str]) -> None:
    """Verify registration password error text does not visually overlap helper text (NFT-USE-01)."""
    # Navigate to the registration page
    _visit(desktop_page, target_urls[2], ".auth-page")
    
    # Click 'Create account' with empty inputs to trigger inline validation errors
    submit_button = desktop_page.get_by_role("button", name="Create account", exact=True)
    submit_button.click()
    
    # Locate the error message and helper text
    error_msg = desktop_page.locator("text=Password is required")
    helper_txt = desktop_page.locator("text=Use 8+ characters")
    
    expect(error_msg).to_be_visible()
    expect(helper_txt).to_be_visible()
    
    error_bounds = error_msg.bounding_box()
    helper_bounds = helper_txt.bounding_box()
    
    assert error_bounds is not None, "Error message bounding box could not be calculated"
    assert helper_bounds is not None, "Helper text bounding box could not be calculated"
    
    # Calculate bottom edge of error message (y-position + height)
    error_bottom = error_bounds["y"] + error_bounds["height"]
    
    # Assert the error message ends before or at the top edge of helper text
    assert error_bottom <= helper_bounds["y"], (
        f"Visual text collision detected! Error bottom ({error_bottom:.1f}px) "
        f"overlaps helper top ({helper_bounds['y']:.1f}px)"
    )		