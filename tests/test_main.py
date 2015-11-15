"""Test main() function."""

import os
from distutils.spawn import find_executable

import httpretty
import py
import pytest

import appveyor_artifacts

try:
    import subprocess32 as subprocess
except ImportError:
    import subprocess

PREFIX = appveyor_artifacts.API_PREFIX + '/buildjobs/%s/artifacts/%s'


def test_no_paths(monkeypatch, caplog):
    """Test when there's nothing to download.

    :param monkeypatch: pytest fixture.
    :param caplog: pytest extension fixture.
    """
    monkeypatch.setattr('appveyor_artifacts.get_urls', lambda _: dict())
    monkeypatch.setattr('appveyor_artifacts.validate', lambda _: None)
    appveyor_artifacts.main(dict(mangle_coverage=False))
    assert caplog.records[-2].message == 'No artifacts; nothing to download.'


@pytest.mark.httpretty
def test_one_file(capsys, monkeypatch, tmpdir, caplog):
    """Test downloading one file.

    :param capsys: pytest fixture.
    :param monkeypatch: pytest fixture.
    :param tmpdir: pytest fixture.
    :param caplog: pytest extension fixture.
    """
    paths_and_urls = {str(tmpdir.join('README.md')): (PREFIX % ('abc1def2ghi3jkl4', 'README.md'), 1234)}
    for url, body in ((u, iter(['.' * s])) for u, s in paths_and_urls.values()):
        httpretty.register_uri(httpretty.GET, url, body=body, streaming=True)
    monkeypatch.setattr('appveyor_artifacts.get_urls', lambda _: paths_and_urls)
    monkeypatch.setattr('appveyor_artifacts.validate', lambda _: None)
    appveyor_artifacts.main(dict(mangle_coverage=False))

    messages = [r.message for r in caplog.records if r.levelname != 'DEBUG']
    expected = [
        'Downloading file (1 dot ~ 1 KiB):',
        'Downloaded 1 file(s), 1234 bytes total.',
    ]
    assert messages == expected

    stdout, stderr = capsys.readouterr()
    assert not stdout
    assert stderr == ' => README.md .. 1234 bytes\n'


@pytest.mark.httpretty
def test_multiple_files(capsys, monkeypatch, tmpdir, caplog):
    """Test downloading multiple files.

    :param capsys: pytest fixture.
    :param monkeypatch: pytest fixture.
    :param tmpdir: pytest fixture.
    :param caplog: pytest extension fixture.
    """
    paths_and_urls = {
        str(tmpdir.join('one.bin')): (PREFIX % ('abc1def2ghi3jkl4', 'one.bin'), 12345),
        str(tmpdir.join('three.bin')): (PREFIX % ('abc1def2ghi3jkl4', 'three.bin'), 123456),
        str(tmpdir.join('eleven.bin')): (PREFIX % ('abc1def2ghi3jkl4', 'eleven.bin'), 123457),
        str(tmpdir.join('eighteen.bin')): (PREFIX % ('abc1def2ghi3jkl4', 'eighteen.bin'), 543210),
    }
    for url, body in ((u, iter(['.' * s])) for u, s in paths_and_urls.values()):
        httpretty.register_uri(httpretty.GET, url, body=body, streaming=True)
    monkeypatch.setattr('appveyor_artifacts.get_urls', lambda _: paths_and_urls)
    monkeypatch.setattr('appveyor_artifacts.validate', lambda _: None)
    appveyor_artifacts.main(dict(mangle_coverage=False))

    messages = [r.message for r in caplog.records if r.levelname != 'DEBUG']
    expected = [
        'Downloading files (1 dot ~ 10 KiB):',
        'Downloaded 4 file(s), 802468 bytes total.',
    ]
    assert messages == expected

    stdout, stderr = capsys.readouterr()
    expected = (
        ' => one.bin .. 12345 bytes\n'
        ' => three.bin ............ 123456 bytes\n'
        ' => eleven.bin ............ 123457 bytes\n'
        ' => eighteen.bin ................................................... 543210 bytes\n'
    )
    assert not stdout
    assert stderr == expected


@pytest.mark.httpretty
def test_small_files(capsys, monkeypatch, tmpdir, caplog):
    """Test downloading multiple small files.

    :param capsys: pytest fixture.
    :param monkeypatch: pytest fixture.
    :param tmpdir: pytest fixture.
    :param caplog: pytest extension fixture.
    """
    paths_and_urls = {
        str(tmpdir.join('one.bin')): (PREFIX % ('abc1def2ghi3jkl4', 'one.bin'), 39),
        str(tmpdir.join('three.bin')): (PREFIX % ('abc1def2ghi3jkl4', 'three.bin'), 28),
        str(tmpdir.join('eleven.bin')): (PREFIX % ('abc1def2ghi3jkl4', 'eleven.bin'), 17),
        str(tmpdir.join('eighteen.bin')): (PREFIX % ('abc1def2ghi3jkl4', 'eighteen.bin'), 6),
        str(tmpdir.join('twenty.bin')): (PREFIX % ('abc1def2ghi3jkl4', 'twenty.bin'), 3),
    }
    for url, body in ((u, iter(['.' * s])) for u, s in paths_and_urls.values()):
        httpretty.register_uri(httpretty.GET, url, body=body, streaming=True)
    monkeypatch.setattr('appveyor_artifacts.get_urls', lambda _: paths_and_urls)
    monkeypatch.setattr('appveyor_artifacts.validate', lambda _: None)
    appveyor_artifacts.main(dict(mangle_coverage=False))

    messages = [r.message for r in caplog.records if r.levelname != 'DEBUG']
    expected = [
        'Downloading files (1 dot ~ 1 KiB):',
        'Downloaded 5 file(s), 93 bytes total.',
    ]
    assert messages == expected

    stdout, stderr = capsys.readouterr()
    expected = (
        ' => twenty.bin . 3 bytes\n'
        ' => eighteen.bin . 6 bytes\n'
        ' => eleven.bin . 17 bytes\n'
        ' => three.bin . 28 bytes\n'
        ' => one.bin . 39 bytes\n'
    )
    assert not stdout
    assert stderr == expected


@pytest.mark.httpretty
def test_large_files(capsys, monkeypatch, tmpdir, caplog):
    """Test downloading multiple large files.

    :param capsys: pytest fixture.
    :param monkeypatch: pytest fixture.
    :param tmpdir: pytest fixture.
    :param caplog: pytest extension fixture.
    """
    paths_and_urls = {
        str(tmpdir.join('fifty_three.bin')): (PREFIX % ('abc1def2ghi3jkl4', 'fifty_three.bin'), 55574528),
        str(tmpdir.join('seventy_one.bin')): (PREFIX % ('abc1def2ghi3jkl4', 'seventy_one.bin'), 74448896),
    }
    for url, body in ((u, iter(['.' * s])) for u, s in paths_and_urls.values()):
        httpretty.register_uri(httpretty.GET, url, body=body, streaming=True)
    monkeypatch.setattr('appveyor_artifacts.get_urls', lambda _: paths_and_urls)
    monkeypatch.setattr('appveyor_artifacts.validate', lambda _: None)
    appveyor_artifacts.main(dict(mangle_coverage=True))

    messages = [r.message for r in caplog.records if r.levelname != 'DEBUG']
    expected = [
        'Downloading files (1 dot ~ 1024 KiB):',
        'Downloaded 2 file(s), 130023424 bytes total.',
    ]
    assert messages == expected

    stdout, stderr = capsys.readouterr()
    expected = (
        ' => fifty_three.bin ..................................................... 55574528 bytes\n'
        ' => seventy_one.bin ....................................................................... 74448896 bytes\n'
    )
    assert not stdout
    assert stderr == expected


@pytest.mark.skipif('(os.environ.get("CI"), os.environ.get("TRAVIS")) != ("true", "true")')
@pytest.mark.parametrize('direct', [False, True])
def test_subprocess(tmpdir, direct):
    """Test executing script through entry_points and directly.

    :param tmpdir: pytest fixture.
    :param bool direct: Execute script directly or through setuptools entrypoint.
    """
    if direct:
        script = os.path.realpath(appveyor_artifacts.__file__).replace('.pyc', '.py')
    else:
        script = find_executable('appveyor-artifacts')
    assert os.path.isfile(script)

    command = [script, '-C', str(tmpdir), '-n', 'appveyor-artifacts-hyf37', 'download']
    with open(os.devnull) as devnull:
        subprocess.check_output(command, stderr=subprocess.STDOUT, stdin=devnull)

    root = py.path.local(__file__).dirpath().join('..')
    assert sorted(i.basename for i in tmpdir.listdir()) == ['README.rst', 'appveyor_artifacts.py']
    assert tmpdir.join('appveyor_artifacts.py').computehash() == root.join('appveyor_artifacts.py').computehash()
    assert tmpdir.join('README.rst').read() == root.join('README.rst').read()
