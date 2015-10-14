"""Test query_api() function."""

import httpretty
import pytest
import requests

from appveyor_artifacts import HandledError, query_api


@pytest.mark.httpretty
def test_valid():
    """Test working response."""
    url = 'https://ci.appveyor.com/api/projects/team/app'
    httpretty.register_uri(httpretty.GET, url, body='{"project": "test"}')
    actual = query_api(url[27:])
    expected = dict(project='test')
    assert actual == expected


@pytest.mark.httpretty
def test_bad_endpoint(caplog):
    """Test HTTP 404."""
    url = 'https://ci.appveyor.com/api/bad'
    error_message = "No HTTP resource was found that matches the request URI '{0}'.".format(url)
    httpretty.register_uri(httpretty.GET, url, body='{"message": "%s"}' % error_message, status=404)
    with pytest.raises(HandledError):
        query_api(url[27:])
    records = [r.message for r in caplog.records() if r.levelname == 'ERROR']
    assert records == ['HTTP 404: ' + error_message]


@pytest.mark.httpretty
def test_unknown_json(caplog):
    """Test HTTP 500."""
    url = 'https://ci.appveyor.com/api/bad'
    httpretty.register_uri(httpretty.GET, url, body='{"other": "error"}', status=500)
    with pytest.raises(HandledError):
        query_api(url[27:])
    records = [r.message for r in caplog.records() if r.levelname == 'ERROR']
    assert records == ['HTTP 500: Unknown error: {"other": "error"}']


@pytest.mark.httpretty
def test_non_json(caplog):
    """Test when API returns something other than JSON."""
    url = 'https://ci.appveyor.com/api/projects/team/app'
    httpretty.register_uri(httpretty.GET, url, body='<html></html>')
    with pytest.raises(HandledError):
        query_api(url[27:])
    records = [r.message for r in caplog.records() if r.levelname == 'ERROR']
    assert records == ['Failed to parse JSON: <html></html>']


@pytest.mark.httpretty
def test_timeout(caplog):
    """Test if API is unresponsive."""
    def timeout(*_):
        """Raise timeout."""
        raise requests.Timeout('Connection timed out.')
    url = 'https://ci.appveyor.com/api/projects/team/app'
    httpretty.register_uri(httpretty.GET, url, body=timeout)
    with pytest.raises(HandledError):
        query_api(url[27:])
    records = [r.message for r in caplog.records() if r.levelname == 'ERROR']
    assert records == ['Timed out waiting for reply from server.']
