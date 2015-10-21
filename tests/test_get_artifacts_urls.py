"""Test get_artifacts_urls() function."""

from functools import partial

from appveyor_artifacts import API_PREFIX, get_artifacts_urls


def mock_query_api(url, replies):
    """Mock JSON replies."""
    return replies[url]


def test_empty(monkeypatch):
    """Test on jobs with no artifacts."""
    monkeypatch.setattr('appveyor_artifacts.query_api', lambda _: list())
    config = dict(always_job_dirs=False, no_job_dirs=None, dir=None)
    assert get_artifacts_urls(config, ['spfxkimxcj6faq57']) == dict()


def test_one(monkeypatch, tmpdir):
    """Test with one artifact."""
    reply = [{'fileName': '.coverage', 'size': 1692, 'type': 'File'}]
    monkeypatch.setattr('appveyor_artifacts.query_api', lambda _: reply)

    config = dict(always_job_dirs=False, no_job_dirs=None, dir=str(tmpdir))
    actual = get_artifacts_urls(config, ['spfxkimxcj6faq57'])
    expected = dict([
        (str(tmpdir.join('.coverage')), (API_PREFIX + '/buildjobs/spfxkimxcj6faq57/artifacts/.coverage', 1692)),
    ])
    assert actual == expected


def test_two(monkeypatch, tmpdir):
    """Test with two artifacts in one job."""
    reply = [
        {'fileName': 'appveyor_artifacts.py', 'size': 12479, 'type': 'File'},
        {'fileName': 'README.rst', 'name': 'readme_file.rst', 'size': 1270, 'type': 'File'}
    ]
    monkeypatch.setattr('appveyor_artifacts.query_api', lambda _: reply)

    config = dict(always_job_dirs=False, no_job_dirs=None, dir=str(tmpdir))
    actual = get_artifacts_urls(config, ['spfxkimxcj6faq57'])
    expected = dict([
        (str(tmpdir.join('appveyor_artifacts.py')),
         (API_PREFIX + '/buildjobs/spfxkimxcj6faq57/artifacts/appveyor_artifacts.py', 12479)),
        (str(tmpdir.join('README.rst')), (API_PREFIX + '/buildjobs/spfxkimxcj6faq57/artifacts/README.rst', 1270)),
    ])
    assert actual == expected


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
