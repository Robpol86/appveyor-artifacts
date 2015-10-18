"""Test get_artifacts_urls() function."""

from functools import partial

from appveyor_artifacts import get_artifacts_urls


def mock_query_api(url, replies):
    """Mock JSON replies."""
    return replies[url]


def test_empty(monkeypatch):
    """Test on jobs with no artifacts."""
    monkeypatch.setattr('appveyor_artifacts.query_api', lambda _: list())
    assert get_artifacts_urls(['spfxkimxcj6faq57']) == list()


def test_one(monkeypatch):
    """Test with one artifact."""
    reply = [{'fileName': '.coverage', 'size': 1692, 'type': 'File'}]
    monkeypatch.setattr('appveyor_artifacts.query_api', lambda _: reply)
    actual = get_artifacts_urls(['spfxkimxcj6faq57'])
    expected = [('spfxkimxcj6faq57', '.coverage')]
    assert actual == expected


def test_two(monkeypatch):
    """Test with two artifacts in one job."""
    reply = [
        {'fileName': 'appveyor_artifacts.py', 'size': 12479, 'type': 'File'},
        {'fileName': 'README.rst', 'name': 'readme_file.rst', 'size': 1270, 'type': 'File'}
    ]
    monkeypatch.setattr('appveyor_artifacts.query_api', lambda _: reply)
    actual = get_artifacts_urls(['spfxkimxcj6faq57'])
    expected = [('spfxkimxcj6faq57', 'appveyor_artifacts.py'), ('spfxkimxcj6faq57', 'README.rst')]
    assert actual == expected


def test_multiple_jobs(monkeypatch):
    """Test with multiple jobs.

    From: https://ci.appveyor.com/project/racker-buildbot/luv
    """
    replies = {
        '/buildjobs/v5wnn9k8auqcqovw/artifacts': [
            {'fileName': 'luajit.exe', 'size': 675840, 'type': 'File'},
            {'fileName': 'luv.dll', 'size': 891392, 'type': 'File'}],
        '/buildjobs/bpgcbvqmawv1jw06/artifacts': [
            {'fileName': 'luajit.exe', 'size': 539136, 'type': 'File'},
            {'fileName': 'luv.dll', 'size': 718336, 'type': 'File'}],
    }
    monkeypatch.setattr('appveyor_artifacts.query_api', partial(mock_query_api, replies=replies))
    actual = get_artifacts_urls(['v5wnn9k8auqcqovw', 'bpgcbvqmawv1jw06'])
    expected = [
        ('v5wnn9k8auqcqovw', 'luajit.exe'),
        ('v5wnn9k8auqcqovw', 'luv.dll'),
        ('bpgcbvqmawv1jw06', 'luajit.exe'),
        ('bpgcbvqmawv1jw06', 'luv.dll'),
    ]
    assert actual == expected


def test_subdirectory(monkeypatch):
    """Test with artifact "file names" being file paths with subdirectories.

    From: https://ci.appveyor.com/project/sayedihashimi/package-web
    """
    reply = [{'fileName': 'src/OutputRoot/PackageWeb.1.1.17.nupkg', 'size': 60301, 'type': 'NuGetPackage'}]
    monkeypatch.setattr('appveyor_artifacts.query_api', lambda _: reply)
    actual = get_artifacts_urls(['r97evl3jva2ejs6b'])
    expected = [('r97evl3jva2ejs6b', 'src/OutputRoot/PackageWeb.1.1.17.nupkg')]
    assert actual == expected
