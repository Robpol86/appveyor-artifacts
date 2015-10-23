"""Test get_artifacts_urls() function."""

from functools import partial

import py
import pytest

from appveyor_artifacts import API_PREFIX, get_artifacts_urls


def mock_query_api(url, replies):
    """Mock JSON replies."""
    return replies[url]


def test_empty(monkeypatch):
    """Test on jobs with no artifacts."""
    monkeypatch.setattr('appveyor_artifacts.query_api', lambda _: list())
    config = dict(always_job_dirs=False, no_job_dirs=None, dir=None)
    assert get_artifacts_urls(config, ['spfxkimxcj6faq57']) == dict()


@pytest.mark.parametrize('always_job_dirs,dir_', [(False, None), (True, py.path.local(__file__).dirpath())])
def test_one(monkeypatch, caplog, always_job_dirs, dir_):
    """Test with one artifact."""
    reply = [{'fileName': '.coverage', 'size': 1692, 'type': 'File'}]
    monkeypatch.setattr('appveyor_artifacts.query_api', lambda _: reply)

    config = dict(always_job_dirs=always_job_dirs, no_job_dirs=None, dir=str(dir_) if dir_ else None)
    actual = get_artifacts_urls(config, ['spfxkimxcj6faq57'])

    expected_local_path = dir_.join('.coverage') if dir_ else py.path.local('.coverage')
    if always_job_dirs:
        expected_local_path = expected_local_path.dirpath().join('spfxkimxcj6faq57', '.coverage')
    expected = {str(expected_local_path): (API_PREFIX + '/buildjobs/spfxkimxcj6faq57/artifacts/.coverage', 1692)}
    assert actual == expected

    messages = [r.message for r in caplog.records()]
    if always_job_dirs:
        assert 'Only one job ID, automatically setting job_dirs = False.' not in messages
    else:
        assert 'Only one job ID, automatically setting job_dirs = False.' in messages


@pytest.mark.parametrize('no_job_dirs', ['', 'skip'])
def test_two(monkeypatch, caplog, no_job_dirs):
    """Test with two artifacts in one job."""
    reply = [
        {'fileName': 'artifacts.py', 'size': 12479, 'type': 'File'},
        {'fileName': 'README.rst', 'name': 'readme_file.rst', 'size': 1270, 'type': 'File'}
    ]
    monkeypatch.setattr('appveyor_artifacts.query_api', lambda _: reply)

    config = dict(always_job_dirs=False, no_job_dirs=no_job_dirs, dir=None)
    actual = get_artifacts_urls(config, ['spfxkimxcj6faq57'])
    expected = dict([
        (py.path.local('artifacts.py'), (API_PREFIX + '/buildjobs/spfxkimxcj6faq57/artifacts/artifacts.py', 12479)),
        (py.path.local('README.rst'), (API_PREFIX + '/buildjobs/spfxkimxcj6faq57/artifacts/README.rst', 1270)),
    ])
    assert actual == expected

    messages = [r.message for r in caplog.records()]
    if no_job_dirs:
        assert 'Only one job ID, automatically setting job_dirs = False.' not in messages
    else:
        assert 'Only one job ID, automatically setting job_dirs = False.' in messages


def test_multiple_jobs(monkeypatch, tmpdir):
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

    config = dict(always_job_dirs=False, no_job_dirs=None, dir=str(tmpdir))
    actual = get_artifacts_urls(config, ['v5wnn9k8auqcqovw', 'bpgcbvqmawv1jw06'])
    expected = dict([
        (str(tmpdir.join('v5wnn9k8auqcqovw', 'luajit.exe')),
         (API_PREFIX + '/buildjobs/v5wnn9k8auqcqovw/artifacts/luajit.exe', 675840)),
        (str(tmpdir.join('v5wnn9k8auqcqovw', 'luv.dll')),
         (API_PREFIX + '/buildjobs/v5wnn9k8auqcqovw/artifacts/luv.dll', 891392)),
        (str(tmpdir.join('bpgcbvqmawv1jw06', 'luajit.exe')),
         (API_PREFIX + '/buildjobs/bpgcbvqmawv1jw06/artifacts/luajit.exe', 539136)),
        (str(tmpdir.join('bpgcbvqmawv1jw06', 'luv.dll')),
         (API_PREFIX + '/buildjobs/bpgcbvqmawv1jw06/artifacts/luv.dll', 718336)),
    ])
    assert actual == expected


def test_subdirectory(monkeypatch, tmpdir):
    """Test with artifact "file names" being file paths with subdirectories.

    From: https://ci.appveyor.com/project/sayedihashimi/package-web
    """
    reply = [{'fileName': 'src/OutputRoot/PackageWeb.1.1.17.nupkg', 'size': 60301, 'type': 'NuGetPackage'}]
    monkeypatch.setattr('appveyor_artifacts.query_api', lambda _: reply)

    config = dict(always_job_dirs=False, no_job_dirs=None, dir=str(tmpdir))
    actual = get_artifacts_urls(config, ['r97evl3jva2ejs6b'])
    expected = dict([
        (str(tmpdir.join('src', 'OutputRoot', 'PackageWeb.1.1.17.nupkg')),
         (API_PREFIX + '/buildjobs/r97evl3jva2ejs6b/artifacts/src/OutputRoot/PackageWeb.1.1.17.nupkg', 60301)),
    ])
    assert actual == expected
