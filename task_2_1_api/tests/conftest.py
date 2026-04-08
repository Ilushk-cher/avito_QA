import os
import random
import sys
import time

import pytest

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.api_client import ApiClient

DEFAULT_BASE_URL = "https://qa-internship.avito.com"


def _parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def pytest_addoption(parser):
    parser.addoption(
        "--base-url",
        action="store",
        default=os.getenv("AVITO_BASE_URL", DEFAULT_BASE_URL),
        help="Base URL of the Avito internship API",
    )
    parser.addoption(
        "--max-response-time",
        action="store",
        type=float,
        default=float(os.getenv("AVITO_MAX_RESPONSE_TIME", "5.0")),
        help="Maximum acceptable response time in seconds for lightweight nonfunctional checks",
    )
    parser.addoption(
        "--verify-ssl",
        action="store_true",
        default=_parse_bool(os.getenv("AVITO_VERIFY_SSL"), default=False),
        help="Enable SSL certificate verification for HTTPS requests",
    )
    parser.addoption(
        "--request-timeout",
        action="store",
        type=float,
        default=float(os.getenv("AVITO_REQUEST_TIMEOUT", "20.0")),
        help="Timeout for a single HTTP request in seconds",
    )


@pytest.fixture(scope="session")
def base_url(pytestconfig):
    return pytestconfig.getoption("--base-url")


@pytest.fixture(scope="session")
def max_response_time(pytestconfig):
    return pytestconfig.getoption("--max-response-time")


@pytest.fixture(scope="session")
def verify_ssl(pytestconfig):
    return pytestconfig.getoption("--verify-ssl")


@pytest.fixture(scope="session")
def request_timeout(pytestconfig):
    return pytestconfig.getoption("--request-timeout")


@pytest.fixture(scope="session")
def api_client(base_url, verify_ssl, request_timeout):
    return ApiClient(
        base_url=base_url,
        timeout=request_timeout,
        verify_ssl=verify_ssl,
    )


@pytest.fixture()
def unique_seller_id():
    lower_bound = 111111
    upper_bound = 999999
    timestamp_part = int(time.time() * 1000) % 800000
    random_part = random.randint(0, 999)
    seller_id = lower_bound + (timestamp_part + random_part) % (upper_bound - lower_bound + 1)
    return seller_id


@pytest.fixture()
def item_payload_factory(unique_seller_id):
    counter = {"value": 0}

    def _build(**overrides):
        counter["value"] += 1
        base_payload = {
            "sellerID": unique_seller_id,
            "name": "QA internship item {0}".format(counter["value"]),
            "price": 1000 + counter["value"],
            "statistics": {
                "likes": counter["value"],
                "viewCount": 10 + counter["value"],
                "contacts": 2 + counter["value"],
            },
        }
        base_payload.update(overrides)
        return base_payload

    return _build


@pytest.fixture()
def created_item(api_client, item_payload_factory):
    payload = item_payload_factory()
    create_response = api_client.create_item(payload)
    assert create_response.status_code == 200, create_response.text
    item = create_response.json()
    return payload, item
