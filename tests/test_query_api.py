"""Test query_api() function."""

from appveyor_artifacts import query_api


class MockGet(object):
    """Mock requests.get() and that return object's .json() method."""

    def __init__(self, json):
        """Constructor."""
        self.headers = None
        self.json_data = json
        self.url = None

    def __call__(self, url, headers, **_):
        """Mock requests.get()."""
        self.headers = headers
        self.url = url
        return self

    def json(self):
        """Mock request.get().json function."""
        self.json_data['auth'] = self.headers['authorization']
        self.json_data['url'] = self.url
        return self.json_data


def test_valid(monkeypatch):
    """Test working response."""
    monkeypatch.setattr('requests.get', MockGet(dict(project='test')))
    monkeypatch.setenv('APPVEYOR_API_TOKEN', 'abc123')
    actual = query_api('/projects/team/app')
    expected = dict(auth='Bearer abc123', url='https://ci.appveyor.com/api/projects/team/app', project='test')
    assert actual == expected


def test_bad_endpoint():
    """Test HTTP 400."""
    pass


def test_bad_token():
    """Test bad API token."""
    pass


def test_non_json():
    """Test when API returns something other than JSON."""
    pass


def test_timeout():
    """Test if API is unresponsive."""
    pass


def test_debug_leak_token():
    """Make sure API token doesn't get leaked into logging."""
    pass
