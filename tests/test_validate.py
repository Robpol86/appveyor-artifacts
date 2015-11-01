"""Test validate() function."""

import os

import pytest

from appveyor_artifacts import HandledError, validate


VALID = dict(
    always_job_dirs=False,
    commit='abc1234',
    dir=os.getcwd(),
    job_name='Environment: Python2.7',
    no_job_dirs='skip',
    owner='me',
    pull_request='4',
    repo='antlers',
    tag='v1.2.3',
    verbose=True,
)

VALID_OPPOSITE = dict(
    always_job_dirs=True,
    commit='',
    dir='',
    job_name='',
    no_job_dirs='',
    owner='me',
    pull_request='',
    repo='antlers',
    tag='',
    verbose=False,
)


def test_valid():
    """Test valid config."""
    validate(VALID)
    validate(VALID_OPPOSITE)


def test_bad_mandatory(caplog):
    """Test missing mandatory configs such as repo, owner, etc."""
    config = VALID.copy()
    validate(config)

    # owner
    config['owner'] = 'Inv@lid'
    with pytest.raises(HandledError):
        validate(config)
    assert caplog.records()[-2].message == 'No or invalid repo owner name obtained.'
    config['owner'] = ''
    with pytest.raises(HandledError):
        validate(config)
    assert caplog.records()[-2].message == 'No or invalid repo owner name obtained.'
    config['owner'] = VALID['owner']
    validate(config)

    # repo
    config['repo'] = 'Inv@lid'
    with pytest.raises(HandledError):
        validate(config)
    assert caplog.records()[-2].message == 'No or invalid repo name obtained.'
    config['repo'] = ''
    with pytest.raises(HandledError):
        validate(config)
    assert caplog.records()[-2].message == 'No or invalid repo name obtained.'
    config['repo'] = VALID['repo']
    validate(config)


def test_bad_optional(caplog):
    """Test bad optional configs."""
    config = VALID.copy()
    validate(config)

    # always_job_dirs
    config['always_job_dirs'] = True
    with pytest.raises(HandledError):
        validate(config)
    assert caplog.records()[-2].message == 'Contradiction: --always-job-dirs and --no-job-dirs used.'
    config['always_job_dirs'] = VALID['always_job_dirs']
    validate(config)

    # commit
    config['commit'] = 'invalid'
    with pytest.raises(HandledError):
        validate(config)
    assert caplog.records()[-2].message == 'No or invalid git commit obtained.'
    config['commit'] = VALID['commit']
    validate(config)

    # dir
    config['dir'] = os.path.join(os.getcwd(), 'dir_not_exist')
    with pytest.raises(HandledError):
        validate(config)
    assert caplog.records()[-2].message == "Not a directory or doesn't exist: " + config['dir']
    config['dir'] = VALID['dir']
    validate(config)

    # no_job_dirs
    config['no_job_dirs'] = 'unknown'
    with pytest.raises(HandledError):
        validate(config)
    assert caplog.records()[-2].message == '--no-job-dirs has invalid value. Check --help for valid values.'
    config['no_job_dirs'] = VALID['no_job_dirs']
    validate(config)

    # pull_request
    config['pull_request'] = 'a'
    with pytest.raises(HandledError):
        validate(config)
    assert caplog.records()[-2].message == '--pull-request is not a digit.'
    config['pull_request'] = VALID['pull_request']
    validate(config)

    # tag
    config['tag'] = 'Inv@l*d'
    with pytest.raises(HandledError):
        validate(config)
    assert caplog.records()[-2].message == 'Invalid git tag obtained.'
    config['tag'] = VALID['tag']
    validate(config)
