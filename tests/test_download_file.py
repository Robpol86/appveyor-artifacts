"""Test download_file() function."""

import re

import httpretty
import py
import pytest

from appveyor_artifacts import download_file, HandledError


@pytest.mark.httpretty
def test_success(capsys, tmpdir):
    """No errors.

    :param capsys: pytest fixture.
    :param tmpdir: pytest fixture.
    """
    # Prepare requests module mocking.
    source_file = py.path.local(__file__).dirpath().join('..', 'appveyor_artifacts.py')
    url = 'https://ci.appveyor.com/api/buildjobs/abc1def2ghi3jkl4/artifacts/appveyor_artifacts.py'
    httpretty.register_uri(httpretty.GET, url, body=iter(source_file.readlines()), streaming=True)

    # Run.
    local_path = tmpdir.join('appveyor_artifacts.py')
    download_file(dict(dir=str(tmpdir)), str(local_path), url, source_file.size(), 1024)

    # Check.
    assert local_path.size() == source_file.size()
    assert local_path.computehash() == source_file.computehash()
    stdout, stderr = capsys.readouterr()
    assert not stdout
    assert re.match(r'^ => appveyor_artifacts.py [\.]{15,79} [\d]{5,6} bytes\n$', stderr)


@pytest.mark.httpretty
def test_success_subdir(capsys, tmpdir):
    """Test with subdirectories.

    :param capsys: pytest fixture.
    :param tmpdir: pytest fixture.
    """
    # Prepare requests module mocking.
    source_file = py.path.local(__file__).dirpath().join('..', 'appveyor_artifacts.py')
    url = 'https://ci.appveyor.com/api/buildjobs/abc1def2ghi3jkl4/artifacts/src/files/appveyor_artifacts.py'
    httpretty.register_uri(httpretty.GET, url, body=iter(source_file.readlines()), streaming=True)

    # Run.
    local_path = tmpdir.join('src', 'files', 'appveyor_artifacts.py')
    download_file(dict(dir=str(tmpdir)), str(local_path), url, source_file.size(), 1024)

    # Check.
    assert local_path.size() == source_file.size()
    assert local_path.computehash() == source_file.computehash()
    stdout, stderr = capsys.readouterr()
    assert not stdout
    assert re.match(r'^ => src/files/appveyor_artifacts.py [\.]{15,79} [\d]{5,6} bytes\n$', stderr)


@pytest.mark.httpretty
@pytest.mark.parametrize('file_exists', [True, False])
def test_errors(tmpdir, caplog, file_exists):
    """Test error handling.

    :param tmpdir: pytest fixture.
    :param caplog: pytest extension fixture.
    :param bool file_exists: Create colliding file.
    """
    source_file = py.path.local(__file__).dirpath().join('..', 'appveyor_artifacts.py')
    url = 'https://ci.appveyor.com/api/buildjobs/abc1def2ghi3jkl4/artifacts/appveyor_artifacts.py'
    httpretty.register_uri(httpretty.GET, url, body=iter(source_file.readlines()), streaming=True)

    local_path = tmpdir.join('appveyor_artifacts.py')
    if file_exists:
        local_path.ensure()
    with pytest.raises(HandledError):
        download_file(dict(dir=str(tmpdir)), str(local_path), url, source_file.size() + 32, 1024)

    if file_exists:
        assert caplog.records[-2].message == 'File already exists: ' + str(local_path)
    else:
        message = 'Expected {0} bytes but got {1} bytes instead.'.format(source_file.size() + 32, source_file.size())
        assert caplog.records[-2].message == message
