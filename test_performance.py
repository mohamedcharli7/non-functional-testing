from time import perf_counter

import requests


MAX_RESPONSE_TIME_SECONDS = 0.5
MAX_PAYLOAD_BYTES = int(1.5 * 1024 * 1024)


def test_page_response_latency(
	requests_session: requests.Session, target_urls: list[str]
) -> None:
	for url in target_urls:
		start_time = perf_counter()
		response = requests_session.get(url, timeout=10)
		elapsed_seconds = perf_counter() - start_time

		assert response.status_code == 200, (
			f"{url} returned HTTP {response.status_code}, expected 200"
		)
		assert elapsed_seconds <= MAX_RESPONSE_TIME_SECONDS, (
			f"{url} took {elapsed_seconds:.3f}s, "
			f"exceeding the {MAX_RESPONSE_TIME_SECONDS:.3f}s limit"
		)


def test_payload_size_limit(
	requests_session: requests.Session, target_urls: list[str]
) -> None:
	for url in target_urls:
		response = requests_session.get(url, timeout=10)
		assert response.status_code == 200, (
			f"{url} returned HTTP {response.status_code}, expected 200"
		)

		payload_size = len(response.content)
		assert payload_size < MAX_PAYLOAD_BYTES, (
			f"{url} response body is {payload_size} bytes, "
			f"exceeding the {MAX_PAYLOAD_BYTES}-byte limit"
		)