"""Test get_arguments() function."""

import pytest

from appveyor_artifacts import get_arguments

CI_TRAVIS = {
    'branch': {'environ': dict(TRAVIS='true', TRAVIS_COMMIT='b4861104d70612cde308afc5d92245ee0283ac53',
                               TRAVIS_REPO_SLUG='selfcov/test_python', TRAVIS_PULL_REQUEST='false', TRAVIS_TAG=''),
               'expected': dict(commit='b4861104d70612cde308afc5d92245ee0283ac53', owner='selfcov',
                                repo='test-python')},
    'pr': {'environ': dict(TRAVIS='true', TRAVIS_COMMIT='779a4cf3e22f77e98a1c01bfd401a5e10f8269ea',
                           TRAVIS_REPO_SLUG='selfcov/test_python', TRAVIS_PULL_REQUEST='1', TRAVIS_TAG=''),
           'expected': dict(commit='779a4cf3e22f77e98a1c01bfd401a5e10f8269ea', owner='selfcov', pull_request='1',
                            repo='test-python')},
    'tag': {'environ': dict(TRAVIS='true', TRAVIS_COMMIT='b4861104d70612cde308afc5d92245ee0283ac53',
                            TRAVIS_REPO_SLUG='selfcov/test_python', TRAVIS_PULL_REQUEST='false', TRAVIS_TAG='v0.0.0'),
            'expected': dict(commit='b4861104d70612cde308afc5d92245ee0283ac53', owner='selfcov', tag='v0.0.0',
                             repo='test-python')}
}


def different_cli_argv():
    """Yield three different sets of command line arguments."""
    # First yield scenario where the user specified no command line arguments.
    argv = []
    expected = {
        'always_job_dirs': False,
        'commit': '',
        'dir': '',
        'ignore_errors': False,
        'job_name': '',
        'mangle_coverage': False,
        'no_job_dirs': '',
        'owner': '',
        'pull_request': '',
        'raise': False,
        'repo': '',
        'tag': '',
        'verbose': False,
    }
    yield argv, expected

    # Next the user specifies some overriding command line arguments.
    argv = [
        '-c', 'abc1234',
        '-j',
        '-n', 'koala',
        '-o', 'me',
        '-p', '1',
        '-t', 'v1.0.0',
    ]
    expected = {
        'always_job_dirs': True,
        'commit': 'abc1234',
        'dir': '',
        'job_name': '',
        'mangle_coverage': False,
        'no_job_dirs': '',
        'owner': 'me',
        'pull_request': '1',
        'raise': False,
        'repo': 'koala',
        'tag': 'v1.0.0',
        'verbose': False,
        'ignore_errors': False,
    }
    yield argv, expected

    # Finally the user specifies the remaining unused arguments.
    argv = [
        '-C', '/tmp',
        '-i',
        '-J', 'overwrite',
        '-m',
        '-N', r'Environment: PYTHON=C:\Python27',
        '-v',
    ]
    expected = {
        'always_job_dirs': False,
        'commit': '',
        'dir': '/tmp',
        'ignore_errors': True,
        'job_name': r'Environment: PYTHON=C:\Python27',
        'mangle_coverage': True,
        'no_job_dirs': 'overwrite',
        'owner': '',
        'pull_request': '',
        'raise': False,
        'repo': '',
        'tag': '',
        'verbose': True,
    }
    yield argv, expected


@pytest.mark.parametrize('argv,expected', different_cli_argv())
def test_no_env(argv, expected):
    """Test outside of any supported CI env."""
    environ = dict(PATH='.')
    actual = get_arguments(['download'] + argv, environ)
    assert actual == expected


@pytest.mark.parametrize('ci', [CI_TRAVIS, ])
@pytest.mark.parametrize('kind', ['branch', 'pr', 'tag'])
@pytest.mark.parametrize('argv,expected', different_cli_argv())
def test_ci(argv, expected, kind, ci):
    """Test CI env."""
    environ = ci[kind]['environ']
    expected = expected.copy()

    # Apply expected updates when environment variables are not being overridden.
    if '-c' not in argv:
        expected.update(ci[kind]['expected'])

    actual = get_arguments(['download'] + argv, environ)
    assert actual == expected
