"""Test query_api() function."""

import socket

import httpretty
import pytest

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
    """Test HTTP 404.

    :param caplog: pytest extension fixture.
    """
    url = 'https://ci.appveyor.com/api/bad'
    error_message = "No HTTP resource was found that matches the request URI '{0}'.".format(url)
    httpretty.register_uri(httpretty.GET, url, body='{"message": "%s"}' % error_message, status=404)
    with pytest.raises(HandledError):
        query_api(url[27:])
    records = [r.message for r in caplog.records if r.levelname == 'ERROR']
    assert records == ['HTTP 404: ' + error_message]


@pytest.mark.httpretty
def test_unknown_json(caplog):
    """Test HTTP 500.

    :param caplog: pytest extension fixture.
    """
    url = 'https://ci.appveyor.com/api/bad'
    httpretty.register_uri(httpretty.GET, url, body='{"other": "error"}', status=500)
    with pytest.raises(HandledError):
        query_api(url[27:])
    records = [r.message for r in caplog.records if r.levelname == 'ERROR']
    assert records == ['HTTP 500: Unknown error: {"other": "error"}']


@pytest.mark.httpretty
def test_non_json(caplog):
    """Test when API returns something other than JSON.

    :param caplog: pytest extension fixture.
    """
    url = 'https://ci.appveyor.com/api/projects/team/app'
    httpretty.register_uri(httpretty.GET, url, body='<html></html>')
    with pytest.raises(HandledError):
        query_api(url[27:])
    records = [r.message for r in caplog.records if r.levelname == 'ERROR']
    assert records == ['Failed to parse JSON: <html></html>']


@pytest.mark.parametrize('mode', ['Timeout', 'ConnectionError'])
def test_timeout_and_error(monkeypatch, request, caplog, mode):
    """Test if API is unresponsive.

    Test retry on ConnectionError.

    :param monkeypatch: pytest fixture.
    :param request: pytest fixture.
    :param caplog: pytest extension fixture.
    :param str mode: Scenario to test for.
    """
    server = socket.socket()
    server.bind(('127.0.0.1', 0))
    server.listen(1)
    host_port = '{}:{}'.format(*server.getsockname())
    if mode == 'Timeout':
        request.addfinalizer(lambda: server.close())
    else:
        server.close()  # Opened just to get unused port number.
    monkeypatch.setattr('appveyor_artifacts.API_PREFIX', 'http://{}/api'.format(host_port))
    if mode == 'Timeout':
        monkeypatch.setattr('appveyor_artifacts.QUERY_ATTEMPTS', 1)

    # Test.
    with pytest.raises(HandledError):
        query_api('/projects/team/app')

    # Verify log.
    records = [r.message for r in caplog.records if r.levelname in ('ERROR', 'WARNING')]
    if mode == 'Timeout':
        expected = ['Timed out waiting for reply from server.']
    else:
        expected = [
            'Unable to connect to server.',
            'Network error, retrying in 1 second...',
            'Unable to connect to server.',
            'Network error, retrying in 1 second...',
            'Unable to connect to server.',
        ]
    assert records == expected
