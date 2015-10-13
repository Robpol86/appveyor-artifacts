"""Test query_api() function."""

import pytest

from appveyor_artifacts import HandledError, query_api


class MockGet(object):
    """Mock requests.get() and that return object's .json() method."""

    def __init__(self, json, inject_url=False, status_code=200):
        """Constructor."""
        self.inject_url = inject_url
        self.json_data = json
        self.ok = status_code == 200
        self.status_code = status_code
        self.url = None

    def __call__(self, url, **_):
        """Mock requests.get()."""
        self.url = url
        return self

    def json(self):
        """Mock request.get().json function."""
        if self.inject_url:
            self.json_data['url'] = self.url
        return self.json_data

    @property
    def text(self):
        """Mock request.get().text property."""
        return str(self.json_data)


def test_valid(monkeypatch):
    """Test working response."""
    monkeypatch.setattr('requests.get', MockGet(dict(project='test'), inject_url=True))
    actual = query_api('/projects/team/app')
    expected = dict(url='https://ci.appveyor.com/api/projects/team/app', project='test')
    assert actual == expected


def test_bad_endpoint(monkeypatch, caplog):
    """Test HTTP 404."""
    error_message = "No HTTP resource was found that matches the request URI 'https://ci.appveyor.com/api/bad'."
    monkeypatch.setattr('requests.get', MockGet(dict(message=error_message), status_code=404))
    with pytest.raises(HandledError):
        query_api('/bad')
    records = [r.message for r in caplog.records() if r.levelname == 'ERROR']
    assert records == ['HTTP 404: ' + error_message]


def test_non_json():
    """Test when API returns something other than JSON."""
    pass


def test_timeout():
    """Test if API is unresponsive."""
    pass
