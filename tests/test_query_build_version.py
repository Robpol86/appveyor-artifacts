"""Test query_build_version()."""

from functools import partial

import pytest

from appveyor_artifacts import HandledError, query_build_version


def mock_query_api(url, replies):
    """Mock JSON replies.

    :param str url: Url as key.
    :param dict replies: Mock replies from test functions.
    """
    return replies[url]


@pytest.mark.parametrize('kind', ['branch', 'pull request', 'tag'])
def test_success(monkeypatch, caplog, kind):
    """Test success workflow.

    :param monkeypatch: pytest fixture.
    :param caplog: pytest extension fixture.
    :param str kind: Type of change triggering a Travis CI build.
    """
    replies = {
        '/projects/user/repo/history?recordsNumber=10': dict(builds=[
            {'branch': 'master', 'commitId': '88915f2234998423a713019ac699c3fdf70b48d1', 'isTag': False, 'jobs': [],
             'version': '1.0.239'},
            {'branch': 'master', 'commitId': '5297add4d5225669191aef469474774969549019', 'isTag': False, 'jobs': [],
             'version': '1.0.237', 'pullRequestId': '12'},
            {'branch': 'master', 'commitId': 'c4f19d2996ed1ab027b342dd0685157e3572679d', 'isTag': True, 'jobs': [],
             'version': '1.0.235', 'tag': 'v2.0.0'},
        ]),
    }
    monkeypatch.setattr('appveyor_artifacts.query_api', partial(mock_query_api, replies=replies))

    config = dict(
        commit='88915f2234998423a713019ac699c3fdf70b48d1' if kind == 'branch' else '',
        job_name='',
        owner='user',
        pull_request='12' if kind == 'pull request' else '',
        repo='repo',
        tag='v2.0.0' if kind == 'tag' else '',
    )

    actual = query_build_version(config)
    if kind == 'tag':
        expected = '1.0.235'
    elif kind == 'pull request':
        expected = '1.0.237'
    else:
        expected = '1.0.239'
    assert actual == expected

    messages = [r.message for r in caplog.records if 'This is a' in r.message]
    assert messages == ['This is a {0} build.'.format(kind)]


def test_empty(monkeypatch):
    """Test when there are no matching builds.

    :param monkeypatch: pytest fixture.
    """
    replies = {
        '/projects/user/repo/history?recordsNumber=10': dict(builds=[
            {'branch': 'master', 'commitId': '88915f2234998423a713019ac699c3fdf70b48d1', 'isTag': False, 'jobs': [],
             'status': 'success', 'version': '1.0.239'},
            {'branch': 'master', 'commitId': '5297add4d5225669191aef469474774969549019', 'isTag': False, 'jobs': [],
             'status': 'success', 'version': '1.0.237', 'pullRequestId': '12'},
            {'branch': 'master', 'commitId': 'c4f19d2996ed1ab027b342dd0685157e3572679d', 'isTag': True, 'jobs': [],
             'status': 'success', 'version': '1.0.235', 'tag': 'v2.0.0'},
        ]),
    }
    monkeypatch.setattr('appveyor_artifacts.query_api', partial(mock_query_api, replies=replies))

    config = dict(
        commit='0123456789101112131415161718192021222324',
        job_name='',
        owner='user',
        pull_request=None,
        repo='repo',
        tag='',
    )

    actual = query_build_version(config)
    expected = None
    assert actual == expected

    replies['/projects/user/repo/history?recordsNumber=10']['builds'][:] = []
    actual = query_build_version(config)
    expected = None
    assert actual == expected


def test_errors(monkeypatch, caplog):
    """Test handled exceptions.

    :param monkeypatch: pytest fixture.
    :param caplog: pytest extension fixture.
    """
    replies = {
        '/projects/user/repo/history?recordsNumber=10': dict(),
        '/projects/user/repo/build/1.6.0.43': dict(),
    }
    monkeypatch.setattr('appveyor_artifacts.query_api', partial(mock_query_api, replies=replies))

    config = dict(
        commit='9b1df471879c0caae0594539d0ad87aab06a1ecd',
        job_name='',
        owner='user',
        pull_request=None,
        repo='repo',
        tag='',
    )

    with pytest.raises(HandledError):
        query_build_version(config)
    assert caplog.records[-2].message == 'Bad JSON reply: "builds" key missing.'
