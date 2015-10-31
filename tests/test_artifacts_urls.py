"""Test artifacts_urls() function."""

import re

import py
import pytest

from appveyor_artifacts import API_PREFIX, artifacts_urls, HandledError


@pytest.mark.parametrize('always_job_dirs,dir_', [(False, None), (True, py.path.local(__file__).dirpath())])
def test_one(caplog, always_job_dirs, dir_):
    """Test with one artifact."""
    jobs_artifacts = [('spfxkimxcj6faq57', '.coverage', 1692)]
    config = dict(always_job_dirs=always_job_dirs, no_job_dirs=None, dir=str(dir_) if dir_ else None)
    actual = artifacts_urls(config, jobs_artifacts)

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
def test_two(caplog, no_job_dirs):
    """Test with two artifacts in one job."""
    jobs_artifacts = [('spfxkimxcj6faq57', 'artifacts.py', 12479), ('spfxkimxcj6faq57', 'README.rst', 1270)]
    config = dict(always_job_dirs=False, no_job_dirs=no_job_dirs, dir=None)
    actual = artifacts_urls(config, jobs_artifacts)
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
def test_multiple_jobs(caplog, no_job_dirs):
    """Test with multiple jobs.

    From: https://ci.appveyor.com/project/racker-buildbot/luv
    """
    jobs_artifacts = [
        ('v5wnn9k8auqcqovw', 'luajit.exe', 675840), ('v5wnn9k8auqcqovw', 'luv.dll', 891392),
        ('v5wnn9k8auqcqovw', '.coverage', 123), ('v5wnn9k8auqcqovw', 'no_ext', 456),
        ('bpgcbvqmawv1jw06', 'luajit.exe', 539136), ('bpgcbvqmawv1jw06', 'luv.dll', 718336),
        ('bpgcbvqmawv1jw06', '.coverage', 789), ('bpgcbvqmawv1jw06', 'no_ext', 101),
    ]
    config = dict(always_job_dirs=False, no_job_dirs=no_job_dirs, dir=None)

    # Handle collision.
    if no_job_dirs == 'unknown':
        with pytest.raises(HandledError):
            artifacts_urls(config, jobs_artifacts)
        assert caplog.records()[-2].message.startswith('Collision:')
        return

    actual = artifacts_urls(config, jobs_artifacts)
    expected = dict()
    messages = [r.message for r in caplog.records()]

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


def test_subdirectory():
    """Test with artifact "file names" being file paths with subdirectories.

    From: https://ci.appveyor.com/project/sayedihashimi/package-web
    """
    jobs_artifacts = [
        ('r97evl3jva2ejs6b', 'src/OutputRoot/PackageWeb.1.1.17.nupkg', 60301),
        ('s97evl3jva2ejs6b', 'src/OutputRoot/PackageWeb.1.1.10.nupkg', 50301),
    ]
    config = dict(always_job_dirs=False, no_job_dirs=None, dir=None)
    actual = artifacts_urls(config, jobs_artifacts)
    expected = dict([
        (py.path.local('src/OutputRoot/PackageWeb.1.1.17.nupkg'),
         (API_PREFIX + '/buildjobs/r97evl3jva2ejs6b/artifacts/src/OutputRoot/PackageWeb.1.1.17.nupkg', 60301)),
        (py.path.local('src/OutputRoot/PackageWeb.1.1.10.nupkg'),
         (API_PREFIX + '/buildjobs/s97evl3jva2ejs6b/artifacts/src/OutputRoot/PackageWeb.1.1.10.nupkg', 50301)),
    ])
    assert actual == expected


def test_multi_rename():
    """Test rename for loop."""
    jobs_artifacts = [
        ('1pfx2im3cj6faq57', 'R.rst', 1270), ('1pfx2im3cj6faq58', 'R.rst', 1271), ('1pfx2im3cj6faq59', 'R.rst', 1272),
        ('1pfx2im3cj6faq57', '.cov1', 2270), ('1pfx2im3cj6faq58', '.cov1', 2271), ('1pfx2im3cj6faq59', '.cov1', 2272),
        ('1pfx2im3cj6faq57', '1cov1', 3270), ('1pfx2im3cj6faq58', '1cov1', 3271), ('1pfx2im3cj6faq59', '1cov1', 3272),
        ('1pfx2im3cj6faq57', '1cov.', 4270), ('1pfx2im3cj6faq58', '1cov.', 4271), ('1pfx2im3cj6faq59', '1cov.', 4272),
    ]
    config = dict(always_job_dirs=False, no_job_dirs='rename', dir=None)
    actual = artifacts_urls(config, jobs_artifacts)
    expected = dict([
        (py.path.local('R.rst'), (API_PREFIX + '/buildjobs/1pfx2im3cj6faq57/artifacts/R.rst', 1270)),
        (py.path.local('R_.rst'), (API_PREFIX + '/buildjobs/1pfx2im3cj6faq58/artifacts/R.rst', 1271)),
        (py.path.local('R__.rst'), (API_PREFIX + '/buildjobs/1pfx2im3cj6faq59/artifacts/R.rst', 1272)),
        (py.path.local('.cov1'), (API_PREFIX + '/buildjobs/1pfx2im3cj6faq57/artifacts/.cov1', 2270)),
        (py.path.local('.cov1_'), (API_PREFIX + '/buildjobs/1pfx2im3cj6faq58/artifacts/.cov1', 2271)),
        (py.path.local('.cov1__'), (API_PREFIX + '/buildjobs/1pfx2im3cj6faq59/artifacts/.cov1', 2272)),
        (py.path.local('1cov1'), (API_PREFIX + '/buildjobs/1pfx2im3cj6faq57/artifacts/1cov1', 3270)),
        (py.path.local('1cov1_'), (API_PREFIX + '/buildjobs/1pfx2im3cj6faq58/artifacts/1cov1', 3271)),
        (py.path.local('1cov1__'), (API_PREFIX + '/buildjobs/1pfx2im3cj6faq59/artifacts/1cov1', 3272)),
        (py.path.local('1cov.'), (API_PREFIX + '/buildjobs/1pfx2im3cj6faq57/artifacts/1cov.', 4270)),
        (py.path.local('1cov_.'), (API_PREFIX + '/buildjobs/1pfx2im3cj6faq58/artifacts/1cov.', 4271)),
        (py.path.local('1cov__.'), (API_PREFIX + '/buildjobs/1pfx2im3cj6faq59/artifacts/1cov.', 4272)),
    ])
    assert actual == expected
