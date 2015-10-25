"""Test get_artifacts_urls() function."""

import re
from functools import partial

import py
import pytest

from appveyor_artifacts import API_PREFIX, get_artifacts_urls, HandledError


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
    expected = {expected_local_path: (API_PREFIX + '/buildjobs/spfxkimxcj6faq57/artifacts/.coverage', 1692)}
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


@pytest.mark.parametrize('no_job_dirs', ['', 'skip', 'overwrite', 'rename', 'unknown'])
def test_multiple_jobs(monkeypatch, caplog, no_job_dirs):
    """Test with multiple jobs.

    From: https://ci.appveyor.com/project/racker-buildbot/luv
    """
    replies = {
        '/buildjobs/v5wnn9k8auqcqovw/artifacts': [
            {'fileName': 'luajit.exe', 'size': 675840, 'type': 'File'},
            {'fileName': 'luv.dll', 'size': 891392, 'type': 'File'},
            {'fileName': '.coverage', 'size': 123, 'type': 'File'},
            {'fileName': 'no_ext', 'size': 456, 'type': 'File'},
        ],
        '/buildjobs/bpgcbvqmawv1jw06/artifacts': [
            {'fileName': 'luajit.exe', 'size': 539136, 'type': 'File'},
            {'fileName': 'luv.dll', 'size': 718336, 'type': 'File'},
            {'fileName': '.coverage', 'size': 789, 'type': 'File'},
            {'fileName': 'no_ext', 'size': 101, 'type': 'File'},
        ],
    }
    monkeypatch.setattr('appveyor_artifacts.query_api', partial(mock_query_api, replies=replies))

    config = dict(always_job_dirs=False, no_job_dirs=no_job_dirs, dir=None)

    if no_job_dirs == 'unknown':
        with pytest.raises(HandledError):
            get_artifacts_urls(config, ['v5wnn9k8auqcqovw', 'bpgcbvqmawv1jw06'])
        assert caplog.records()[-2].message.startswith('Collision:')
        return
    actual = get_artifacts_urls(config, ['v5wnn9k8auqcqovw', 'bpgcbvqmawv1jw06'])
    messages = [r.message for r in caplog.records()]
    expected = dict()

    # Test-specific API URL.
    url = API_PREFIX + '/buildjobs/%s/artifacts/%s'

    if not no_job_dirs:
        assert 'Multiple job IDs with file conflicts, automatically setting job_dirs = True' in messages
        expected[py.path.local('v5wnn9k8auqcqovw/luajit.exe')] = (url % ('v5wnn9k8auqcqovw', 'luajit.exe'), 675840)
        expected[py.path.local('v5wnn9k8auqcqovw/luv.dll')] = (url % ('v5wnn9k8auqcqovw', 'luv.dll'), 891392)
        expected[py.path.local('v5wnn9k8auqcqovw/.coverage')] = (url % ('v5wnn9k8auqcqovw', '.coverage'), 123)
        expected[py.path.local('v5wnn9k8auqcqovw/no_ext')] = (url % ('v5wnn9k8auqcqovw', 'no_ext'), 456)
        expected[py.path.local('bpgcbvqmawv1jw06/luajit.exe')] = (url % ('bpgcbvqmawv1jw06', 'luajit.exe'), 539136)
        expected[py.path.local('bpgcbvqmawv1jw06/luv.dll')] = (url % ('bpgcbvqmawv1jw06', 'luv.dll'), 718336)
        expected[py.path.local('bpgcbvqmawv1jw06/.coverage')] = (url % ('bpgcbvqmawv1jw06', '.coverage'), 789)
        expected[py.path.local('bpgcbvqmawv1jw06/no_ext')] = (url % ('bpgcbvqmawv1jw06', 'no_ext'), 101)
    else:
        assert 'Multiple job IDs with file conflicts, automatically setting job_dirs = True' not in messages

    if no_job_dirs == 'skip':
        assert any(re.match(r'Skipping.*luajit\.exe.*bpgcbvqmawv1jw06', m) for m in messages)
        assert any(re.match(r'Skipping.*luv\.dll.*bpgcbvqmawv1jw06', m) for m in messages)
        assert any(re.match(r'Skipping.*\.coverage.*bpgcbvqmawv1jw06', m) for m in messages)
        assert any(re.match(r'Skipping.*no_ext.*bpgcbvqmawv1jw06', m) for m in messages)
        expected[py.path.local('luajit.exe')] = (url % ('v5wnn9k8auqcqovw', 'luajit.exe'), 675840)
        expected[py.path.local('luv.dll')] = (url % ('v5wnn9k8auqcqovw', 'luv.dll'), 891392)
        expected[py.path.local('.coverage')] = (url % ('v5wnn9k8auqcqovw', '.coverage'), 123)
        expected[py.path.local('no_ext')] = (url % ('v5wnn9k8auqcqovw', 'no_ext'), 456)
    else:
        assert not any(re.match(r'Skipping.*luajit\.exe.*bpgcbvqmawv1jw06', m) for m in messages)
        assert not any(re.match(r'Skipping.*luv\.dll.*bpgcbvqmawv1jw06', m) for m in messages)
        assert not any(re.match(r'Skipping.*\.coverage.*bpgcbvqmawv1jw06', m) for m in messages)
        assert not any(re.match(r'Skipping.*no_ext.*bpgcbvqmawv1jw06', m) for m in messages)

    if no_job_dirs == 'overwrite':
        assert any(re.match(r'Overwriting.*luajit\.exe.*v5wnn9k8auqcqovw.*bpgcbvqmawv1jw06', m) for m in messages)
        assert any(re.match(r'Overwriting.*luv\.dll.*v5wnn9k8auqcqovw.*bpgcbvqmawv1jw06', m) for m in messages)
        assert any(re.match(r'Overwriting.*\.coverage.*v5wnn9k8auqcqovw.*bpgcbvqmawv1jw06', m) for m in messages)
        assert any(re.match(r'Overwriting.*no_ext.*v5wnn9k8auqcqovw.*bpgcbvqmawv1jw06', m) for m in messages)
        expected[py.path.local('luajit.exe')] = (url % ('bpgcbvqmawv1jw06', 'luajit.exe'), 539136)
        expected[py.path.local('luv.dll')] = (url % ('bpgcbvqmawv1jw06', 'luv.dll'), 718336)
        expected[py.path.local('.coverage')] = (url % ('bpgcbvqmawv1jw06', '.coverage'), 789)
        expected[py.path.local('no_ext')] = (url % ('bpgcbvqmawv1jw06', 'no_ext'), 101)
    else:
        assert not any(re.match(r'Overwriting.*luajit\.exe.*v5wnn9k8auqcqovw.*bpgcbvqmawv1jw06', m) for m in messages)
        assert not any(re.match(r'Overwriting.*luv\.dll.*v5wnn9k8auqcqovw.*bpgcbvqmawv1jw06', m) for m in messages)
        assert not any(re.match(r'Overwriting.*\.coverage.*v5wnn9k8auqcqovw.*bpgcbvqmawv1jw06', m) for m in messages)
        assert not any(re.match(r'Overwriting.*no_ext.*v5wnn9k8auqcqovw.*bpgcbvqmawv1jw06', m) for m in messages)

    if no_job_dirs == 'rename':
        assert any(re.match(r'Renaming.*luajit\.exe.*luajit_\.exe.*bpgcbvqmawv1jw06', m) for m in messages)
        assert any(re.match(r'Renaming.*luv\.dll.*luv_\.dll.*bpgcbvqmawv1jw06', m) for m in messages)
        assert any(re.match(r'Renaming.*\.coverage.*\.coverage_.*bpgcbvqmawv1jw06', m) for m in messages)
        assert any(re.match(r'Renaming.*no_ext.*no_ext_.*bpgcbvqmawv1jw06', m) for m in messages)
        expected[py.path.local('luajit.exe')] = (url % ('v5wnn9k8auqcqovw', 'luajit.exe'), 675840)
        expected[py.path.local('luv.dll')] = (url % ('v5wnn9k8auqcqovw', 'luv.dll'), 891392)
        expected[py.path.local('.coverage')] = (url % ('v5wnn9k8auqcqovw', '.coverage'), 123)
        expected[py.path.local('no_ext')] = (url % ('v5wnn9k8auqcqovw', 'no_ext'), 456)
        expected[py.path.local('luajit_.exe')] = (url % ('bpgcbvqmawv1jw06', 'luajit.exe'), 539136)
        expected[py.path.local('luv_.dll')] = (url % ('bpgcbvqmawv1jw06', 'luv.dll'), 718336)
        expected[py.path.local('.coverage_')] = (url % ('bpgcbvqmawv1jw06', '.coverage'), 789)
        expected[py.path.local('no_ext_')] = (url % ('bpgcbvqmawv1jw06', 'no_ext'), 101)
    else:
        assert not any(re.match(r'Renaming.*luajit\.exe.*luajit_\.exe.*bpgcbvqmawv1jw06', m) for m in messages)
        assert not any(re.match(r'Renaming.*luv\.dll.*luv_\.dll.*bpgcbvqmawv1jw06', m) for m in messages)
        assert not any(re.match(r'Renaming.*\.coverage.*\.coverage_.*bpgcbvqmawv1jw06', m) for m in messages)
        assert not any(re.match(r'Renaming.*no_ext.*no_ext_.*bpgcbvqmawv1jw06', m) for m in messages)

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


def test_multi_rename():
    """Test rename for loop."""
    pass
