import re
from time import perf_counter
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import Locator, Page, expect

from conftest import BASE_URL


ONBOARDING_URLS = (
	f"{BASE_URL}/upload",
	f"{BASE_URL}/preferences",
	f"{BASE_URL}/profile/review",
)


def _visit(page: Page, url: str) -> None:
	page.goto(url, wait_until="domcontentloaded")
	expect(page.locator("main")).to_be_visible()


def _visible_top_level_cards(page: Page) -> list:
	candidates = page.locator(
		"main [class*='card' i], main [data-testid*='card' i]"
	)
	cards = []
	for index in range(candidates.count()):
		candidate = candidates.nth(index)
		if not candidate.is_visible():
			continue
		is_nested = candidate.evaluate(
			"(element) => Boolean(element.parentElement?.closest("
			"\"[class*='card' i], [data-testid*='card' i]\"))"
		)
		if not is_nested:
			cards.append(candidate)
	return cards


def _assert_same_row_without_overlap(
	left_bounds: dict, right_bounds: dict, description: str
) -> None:
	assert abs(left_bounds["y"] - right_bounds["y"]) <= 4, (
		f"{description} should be on the same horizontal row"
	)
	assert (
		left_bounds["x"] + left_bounds["width"] <= right_bounds["x"]
		or right_bounds["x"] + right_bounds["width"] <= left_bounds["x"]
	), f"{description} should not overlap"


def _interactive_control(page: Page, name: str) -> Locator:
	button = page.get_by_role("button", name=name, exact=True)
	if button.count():
		return button.first
	link = page.get_by_role("link", name=name, exact=True)
	if link.count():
		return link.first
	text = page.get_by_text(name, exact=True)
	return text.locator(
		"xpath=ancestor-or-self::button | ancestor-or-self::a"
	).first


def _card_for_heading(page: Page, heading: str):
	heading_locator = page.get_by_role("heading", name=heading, exact=True)
	expect(heading_locator).to_be_visible()
	cards = page.locator(
		"main [class*='card' i], main [data-testid*='card' i], main section, main article"
	).filter(has=heading_locator)
	return cards.first


@pytest.mark.parametrize("url", ONBOARDING_URLS)
def test_onboarding_routes_require_authentication(
	desktop_page: Page, url: str
) -> None:
	desktop_page.goto(url, wait_until="networkidle")
	desktop_page.wait_for_timeout(1000)
	final_path = urlsplit(desktop_page.url).path.rstrip("/")
	requested_path = urlsplit(url).path.rstrip("/")
	assert final_path != requested_path or "/login" in final_path, (
		f"Unauthenticated visitor remained on protected route {final_path!r}"
	)


def test_upload_file_constraints_and_oversized_rejection(
	authenticated_desktop_page: Page,
) -> None:
	page = authenticated_desktop_page
	_visit(page, ONBOARDING_URLS[0])

	file_input = page.locator("input[type='file']")
	expect(file_input).to_be_attached()
	accept = (file_input.get_attribute("accept") or "").lower()
	assert ".pdf" in accept, f"File input accept attribute must allow PDF: {accept!r}"
	assert ".docx" in accept or (
		"application/vnd.openxmlformats-officedocument.wordprocessingml.document"
		in accept
	), f"File input accept attribute must allow DOCX: {accept!r}"

	page_errors: list[str] = []
	page.on("pageerror", lambda error: page_errors.append(str(error)))
	file_input.set_input_files(
		{
			"name": "oversized_cv.pdf",
			"mimeType": "application/pdf",
			"buffer": b"0" * (6 * 1024 * 1024),
		}
	)

	expect(page).to_have_url(re.compile(r"/upload(?:[?#]|$)"))
	rejection_message = page.get_by_text(
		re.compile(r"(5\s?MB|too large|maximum|size limit|exceed)", re.IGNORECASE)
	).first
	expect(rejection_message).to_be_visible(timeout=10000)
	assert not page_errors, f"Oversized upload caused a page error: {page_errors}"
	assert urlsplit(page.url).path.rstrip("/") == "/upload", (
		"Oversized upload must not advance to the preferences step"
	)


def test_saved_cv_analysis_transition_latency(
	authenticated_desktop_page: Page,
) -> None:
	page = authenticated_desktop_page
	_visit(page, ONBOARDING_URLS[0])
	start_button = page.get_by_role(
		"button", name="Start analysing CV", exact=True
	)
	expect(start_button).to_be_visible()
	page.get_by_role(
		"combobox", name="Use a saved CV"
	).select_option(label="General_Sample_CV-v2.docx")
	expect(start_button).to_be_enabled()

	start_time = perf_counter()
	start_button.click()
	page.wait_for_function(
		"""() => {
			const path = window.location.pathname.replace(/\\/$/, "");
			const headingVisible = [...document.querySelectorAll("h1, h2, h3")]
				.some((heading) => heading.textContent.trim() ===
					"Confirm your career goals" && heading.getClientRects().length > 0);
			return path === "/preferences" || headingVisible;
		}""",
		timeout=25000,
	)
	elapsed_seconds = perf_counter() - start_time
	assert elapsed_seconds <= 25.0, (
		f"CV analysis transition took {elapsed_seconds:.2f}s, exceeding the 25s SLA"
	)


def test_upload_and_preferences_desktop_layout(
	authenticated_desktop_page: Page,
) -> None:
	page = authenticated_desktop_page
	assert page.evaluate("() => window.innerWidth") == 1440

	panel_headings = (
		(
			ONBOARDING_URLS[0],
			"Upload your resume to start AI matching",
			"Add your resume",
		),
		(
			ONBOARDING_URLS[1],
			"Your resume is taking shape.",
			"Confirm your career goals",
		),
	)
	for url, left_heading_text, right_heading_text in panel_headings:
		_visit(page, url)
		left_heading = page.get_by_role("heading", name=left_heading_text)
		right_heading = page.get_by_role("heading", name=right_heading_text)
		expect(left_heading).to_be_visible()
		expect(right_heading).to_be_visible()
		left_bounds = left_heading.bounding_box()
		right_bounds = right_heading.bounding_box()
		assert left_bounds is not None
		assert right_bounds is not None
		assert left_bounds["x"] + left_bounds["width"] <= right_bounds["x"], (
			f"{left_heading_text!r} panel overlaps or sits to the right of "
			f"{right_heading_text!r} on {url}"
		)

	_visit(page, ONBOARDING_URLS[1])
	location_input = page.get_by_label("Preferred location", exact=True)
	salary_input = page.get_by_label("Minimum salary", exact=True)
	expect(location_input).to_be_visible()
	expect(salary_input).to_be_visible()
	location_bounds = location_input.bounding_box()
	salary_bounds = salary_input.bounding_box()
	assert location_bounds is not None
	assert salary_bounds is not None
	assert abs(location_bounds["y"] - salary_bounds["y"]) <= 4, (
		"Preferred location and Minimum salary inputs should align on the same row"
	)

	back_button = page.get_by_role("link", name="Back", exact=True)
	save_button = page.get_by_role(
		"button", name="Save and continue", exact=True
	)
	expect(back_button).to_be_visible()
	expect(save_button).to_be_visible()
	back_bounds = back_button.bounding_box()
	save_bounds = save_button.bounding_box()
	assert back_bounds is not None
	assert save_bounds is not None
	_assert_same_row_without_overlap(
		back_bounds, save_bounds, "Back and Save and continue buttons"
	)


def test_profile_review_desktop_layout_and_action_bar(
	authenticated_desktop_page: Page,
) -> None:
	page = authenticated_desktop_page
	_visit(page, ONBOARDING_URLS[2])
	expect(
		page.get_by_role("heading", name="Your profile is ready.", exact=True)
	).to_be_visible()

	for heading in (
		"Personal information",
		"Career goals & preferences",
		"Experience & education",
		"Extracted skills",
		"Languages",
	):
		expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()

	cancel_button = _interactive_control(page, "Cancel and reupload CV")
	review_button = page.get_by_role(
		"button", name="Review career goals", exact=True
	)
	expect(cancel_button).to_be_visible()
	expect(review_button).to_be_visible()
	cancel_button.scroll_into_view_if_needed()
	review_button.scroll_into_view_if_needed()
	cancel_bounds = cancel_button.bounding_box()
	review_bounds = review_button.bounding_box()
	assert cancel_bounds is not None
	assert review_bounds is not None
	_assert_same_row_without_overlap(
		cancel_bounds, review_bounds, "Profile review action controls"
	)

	viewport_width = page.evaluate("() => window.innerWidth")
	for name, bounds in (
		("Cancel and reupload CV", cancel_bounds),
		("Review career goals", review_bounds),
	):
		assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= viewport_width, (
			f"{name} must fit inside the {viewport_width}px desktop viewport"
		)


def test_profile_review_accordion_and_chip_containment(
	authenticated_desktop_page: Page,
) -> None:
	page = authenticated_desktop_page
	_visit(page, ONBOARDING_URLS[2])

	skills_card = _card_for_heading(page, "Extracted skills")
	skills_bounds = skills_card.bounding_box()
	assert skills_bounds is not None
	skill_chips = skills_card.locator(
		"[class*='chip' i], [class*='badge' i], [data-testid*='skill' i]"
	)
	visible_chips = [
		skill_chips.nth(index)
		for index in range(skill_chips.count())
		if skill_chips.nth(index).is_visible()
	]
	assert visible_chips, "The Extracted skills card should contain visible skill chips"
	for index, chip in enumerate(visible_chips, start=1):
		chip_bounds = chip.bounding_box()
		assert chip_bounds is not None
		assert chip_bounds["x"] >= skills_bounds["x"], (
			f"Skill chip {index} extends left of the Extracted skills card"
		)
		assert chip_bounds["x"] + chip_bounds["width"] <= (
			skills_bounds["x"] + skills_bounds["width"]
		), f"Skill chip {index} overflows the Extracted skills card"

	experience_card = _card_for_heading(page, "Experience & education")
	accordion = experience_card.get_by_role("button").first
	if accordion.count() == 0:
		accordion = experience_card.locator("details > summary").first
	expect(accordion).to_be_visible()
	accordion.scroll_into_view_if_needed()
	is_native_summary = accordion.evaluate(
		"(element) => element.tagName.toLowerCase() === 'summary'"
	)
	expanded_id = accordion.get_attribute("aria-controls")
	details_container = accordion.locator("xpath=..") if is_native_summary else None
	accordion.click()
	if expanded_id:
		expanded_content = page.locator(f"#{expanded_id}")
	elif is_native_summary:
		assert details_container is not None
		expect(details_container).to_have_attribute("open", "")
		expanded_content = details_container
	else:
		expanded_content = accordion.locator("xpath=following-sibling::*[1]")
		if expanded_content.count() == 0:
			expanded_content = experience_card
		if accordion.get_attribute("aria-expanded") is not None:
			expect(accordion).to_have_attribute("aria-expanded", "true")
	expect(expanded_content).to_be_visible()
	expanded_bounds = expanded_content.bounding_box()
	experience_bounds = experience_card.bounding_box()
	assert expanded_bounds is not None
	assert experience_bounds is not None
	assert expanded_bounds["x"] >= experience_bounds["x"], (
		"Expanded experience content extends left of its card"
	)
	assert expanded_bounds["x"] + expanded_bounds["width"] <= (
		experience_bounds["x"] + experience_bounds["width"]
	), "Expanded experience content exceeds its card width"

	scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
	viewport_width = page.evaluate("() => window.innerWidth")
	assert scroll_width <= viewport_width, (
		f"Expanded accordion causes horizontal page scroll "
		f"({scroll_width}px > {viewport_width}px)"
	)


def test_onboarding_mobile_zero_horizontal_overflow(
	authenticated_mobile_page: Page,
) -> None:
	page = authenticated_mobile_page

	for index, url in enumerate(ONBOARDING_URLS):
		_visit(page, url)
		viewport_width = page.evaluate("() => window.innerWidth")
		assert viewport_width == 375
		if index == 1:
			expect(
				page.get_by_role(
					"heading", name="Confirm your career goals", exact=True
				)
			).to_be_visible()
		elif index == 2:
			expect(
				page.get_by_role(
					"heading", name="Your profile is ready.", exact=True
				)
			).to_be_visible()

		scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
		assert scroll_width <= viewport_width, (
			f"Mobile onboarding page {url} has horizontal overflow: "
			f"scrollWidth={scroll_width}, innerWidth={viewport_width}"
		)


def test_onboarding_mobile_touch_targets_and_viewport_fit(
	authenticated_mobile_page: Page,
) -> None:
	page = authenticated_mobile_page

	targets_by_route = (
		(ONBOARDING_URLS[0], ("Browse files", "Start analysing CV")),
		(ONBOARDING_URLS[1], ("Save and continue",)),
		(ONBOARDING_URLS[2], ("Review career goals",)),
	)
	for url, target_names in targets_by_route:
		_visit(page, url)
		viewport_width = page.evaluate("() => window.innerWidth")
		assert viewport_width == 375
		for name in target_names:
			interactive_control = _interactive_control(page, name)
			expect(interactive_control).to_be_visible()
			interactive_control.scroll_into_view_if_needed()
			bounds = interactive_control.bounding_box()
			assert bounds is not None
			assert (
				bounds["x"] >= 0
				and bounds["x"] + bounds["width"] <= viewport_width
			), (
				f"{name} does not fit within the {viewport_width}px mobile viewport"
			)
			assert bounds["height"] >= 40, (
				f"{name} touch target is only {bounds['height']}px high"
			)git add .