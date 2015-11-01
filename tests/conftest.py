"""Configure tests."""

import sys

import httpretty
import pytest
import requests.packages.urllib3


@pytest.fixture(autouse=True, scope='session')
def config_httpretty():
    """Configure httpretty global variables."""
    httpretty.HTTPretty.allow_net_connect = False


@pytest.fixture(autouse=True, scope='session')
def config_requests():
    """Disable SSL warnings during testing."""
    if sys.version_info[:3] < (2, 7, 9):
        requests.packages.urllib3.disable_warnings()
