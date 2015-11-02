"""Test mangle_coverage() function."""

import pytest

from appveyor_artifacts import HandledError, mangle_coverage


def test_not_coverage_file(tmpdir, caplog):
    """Test non-coverage file."""
    local_path = tmpdir.join('.coverage')
    local_path.write('lol jk')
    old_hash = local_path.computehash()

    mangle_coverage(str(local_path))
    assert caplog.records()[-2].message == 'File {0} not a coverage file.'.format(str(local_path))
    assert local_path.computehash() == old_hash


def test_file_not_found(tmpdir, caplog):
    """Test unrelated coverage file."""
    local_path = tmpdir.join('.coverage')
    local_path.write(
        '!coverage.py: This is a private format, don\'t read it directly!{"arcs": {"C:\\\\projects\\\\'
        'colorclass\\\\colorclass.py": [[516, 509], [398, 401], [173, 174], [-1, 380]]}}'
    )
    old_hash = local_path.computehash()

    with pytest.raises(HandledError):
        mangle_coverage(str(local_path))
    assert caplog.records()[-2].message.startswith('No such file: ')
    assert local_path.computehash() == old_hash


def test_success(tmpdir):
    """Test valid coverage file."""
    local_path = tmpdir.join('.coverage')
    local_path.write(
        '!coverage.py: This is a private format, don\'t read it directly!{"arcs": {"C:\\\\projects\\\\'
        'appveyor_artifacts\\\\appveyor_artifacts.py": [[516, 509], [398, 401], [173, 174], [-1, 380]]}}'
    )
    old_hash = local_path.computehash()

    mangle_coverage(str(local_path))
    assert local_path.computehash() != old_hash
    assert '"C:' not in local_path.read()
