"""Test get_arguments() function."""

import pytest

from appveyor_artifacts import get_arguments

ARGV_OVERRIDE = ['-c', 'abc123', '-o', 'me', '-p', '1', '-r', 'koala', '-t', 'v1.0.0', '-v']

CI_TRAVIS = {
    'branch': {'environ': dict(TRAVIS='true', TRAVIS_COMMIT='b4861104d70612cde308afc5d92245ee0283ac53',
                               TRAVIS_REPO_SLUG='selfcov/test_python', TRAVIS_PULL_REQUEST='false', TRAVIS_TAG=''),
               'expected': dict(commit='b4861104d70612cde308afc5d92245ee0283ac53', owner='selfcov', pull_request=None,
                                repo='test_python', tag='', verbose=False)},
    'pr': {'environ': dict(TRAVIS='true', TRAVIS_COMMIT='779a4cf3e22f77e98a1c01bfd401a5e10f8269ea',
                           TRAVIS_REPO_SLUG='selfcov/test_python', TRAVIS_PULL_REQUEST='1', TRAVIS_TAG=''),
           'expected': dict(commit='779a4cf3e22f77e98a1c01bfd401a5e10f8269ea', owner='selfcov', pull_request=1,
                            repo='test_python', tag='', verbose=False)},
    'tag': {'environ': dict(TRAVIS='true', TRAVIS_COMMIT='b4861104d70612cde308afc5d92245ee0283ac53',
                            TRAVIS_REPO_SLUG='selfcov/test_python', TRAVIS_PULL_REQUEST='false', TRAVIS_TAG='v0.0.0'),
            'expected': dict(commit='b4861104d70612cde308afc5d92245ee0283ac53', owner='selfcov', pull_request=None,
                             repo='test_python', tag='v0.0.0', verbose=False)}
}


@pytest.mark.parametrize('argv', ([], ARGV_OVERRIDE))
def test_no_env(argv):
    """Test outside of any supported CI env."""
    if argv:
        expected = dict(commit='abc123', owner='me', pull_request=1, repo='koala', tag='v1.0.0', verbose=True)
    else:
        expected = dict(commit='', owner='', pull_request=None, repo='', tag='', verbose=False)

    actual = get_arguments(['download'] + argv, dict(PATH='.'))
    assert actual == expected


def test_bad_pull_request():
    """Test if pull request isn't a number."""
    assert get_arguments(['download', '-p', '1234'])['pull_request'] == 1234
    assert get_arguments(['download', '-p', 'toad'])['pull_request'] is None


@pytest.mark.parametrize('ci', [CI_TRAVIS, ])
@pytest.mark.parametrize('kind', ['branch', 'pr', 'tag'])
@pytest.mark.parametrize('argv', ([], ARGV_OVERRIDE))
def test_ci(argv, kind, ci):
    """Test CI env."""
    if argv:
        expected = dict(commit='abc123', owner='me', pull_request=1, repo='koala', tag='v1.0.0', verbose=True)
    else:
        expected = ci[kind]['expected']

    actual = get_arguments(['download'] + argv, ci[kind]['environ'])
    assert actual == expected
