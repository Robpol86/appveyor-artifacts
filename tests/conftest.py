"""Configure tests."""

import httpretty
import pytest


@pytest.fixture(autouse=True, scope='session')
def config_httpretty():
    """Configure httpretty global variables."""
    httpretty.HTTPretty.allow_net_connect = False
