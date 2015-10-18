"""Test get_job_ids()."""

from functools import partial

import pytest

from appveyor_artifacts import get_job_ids, HandledError


def mock_query_api(url, replies):
    """Mock JSON replies."""
    return replies[url]


@pytest.mark.parametrize('kind', ['branch', 'pull request', 'tag'])
def test_success(monkeypatch, caplog, kind):
    """Test success workflow."""
    replies = {
        '/projects/user/repo/history?recordsNumber=10': dict(builds=[
            {'branch': 'master', 'commitId': '88915f2234998423a713019ac699c3fdf70b48d1', 'isTag': False, 'jobs': [],
             'status': 'success', 'version': '1.0.239'},
            {'branch': 'master', 'commitId': '5297add4d5225669191aef469474774969549019', 'isTag': False, 'jobs': [],
             'status': 'success', 'version': '1.0.237', 'pullRequestId': '12'},
            {'branch': 'master', 'commitId': 'c4f19d2996ed1ab027b342dd0685157e3572679d', 'isTag': True, 'jobs': [],
             'status': 'success', 'version': '1.0.235', 'tag': 'v2.0.0'},
        ]),
        '/projects/user/repo/build/1.0.239': dict(build=dict(jobs=[{'jobId': 'ocw0l628ww5yqqxy'}])),
        '/projects/user/repo/build/1.0.237': dict(build=dict(jobs=[{'jobId': 'xsx5g6c7wn64124s'}])),
        '/projects/user/repo/build/1.0.235': dict(build=dict(jobs=[{'jobId': 'nuu3ak30cej138n3'}])),
    }
    monkeypatch.setattr('appveyor_artifacts.query_api', partial(mock_query_api, replies=replies))

    config = dict(
        owner='user',
        repo='repo',
        tag='v2.0.0' if kind == 'tag' else '',
        pull_request=12 if kind == 'pull request' else None,
        commit='88915f2234998423a713019ac699c3fdf70b48d1' if kind == 'branch' else '',
    )

    actual = get_job_ids(config)
    if kind == 'tag':
        expected = (['nuu3ak30cej138n3'], 'success')
    elif kind == 'pull request':
        expected = (['xsx5g6c7wn64124s'], 'success')
    else:
        expected = (['ocw0l628ww5yqqxy'], 'success')
    assert actual == expected

    messages = [r.message for r in caplog.records() if 'This is a' in r.message]
    assert messages == ['This is a {0} build.'.format(kind)]


def test_multiple_jobs(monkeypatch):
    """Test AppVeyor jobs with multiple job IDs."""
    replies = {
        '/projects/paypal/paypal-net-sdk/history?recordsNumber=10': dict(builds=[
            {'branch': 'master', 'commitId': '9b1df471879c0caae0594539d0ad87aab06a1ecd', 'isTag': False, 'jobs': [],
             'status': 'success', 'version': '1.6.0.43'},
        ]),
        '/projects/paypal/paypal-net-sdk/build/1.6.0.43': dict(build=dict(jobs=[
            {'jobId': 'spfxkimxcj6faq57'},
            {'jobId': '932hipuhbdyoycpd'},
            {'jobId': '5r05nfjcamvlss5o'},
        ])),
    }
    monkeypatch.setattr('appveyor_artifacts.query_api', partial(mock_query_api, replies=replies))

    config = dict(
        owner='paypal',
        repo='paypal-net-sdk',
        tag='',
        pull_request=None,
        commit='9b1df471879c0caae0594539d0ad87aab06a1ecd',
    )

    actual = get_job_ids(config)
    expected = (['spfxkimxcj6faq57', '932hipuhbdyoycpd', '5r05nfjcamvlss5o'], 'success')
    assert actual == expected


def test_failed(monkeypatch):
    """Test non-success status."""
    replies = {
        '/projects/user/repo/history?recordsNumber=10': dict(builds=[
            {'branch': 'master', 'commitId': '9b1df471879c0caae0594539d0ad87aab06a1ecd', 'isTag': False, 'jobs': [],
             'status': 'failed', 'version': '1.6.0.43'},
        ]),
    }
    monkeypatch.setattr('appveyor_artifacts.query_api', partial(mock_query_api, replies=replies))

    config = dict(
        owner='user',
        repo='repo',
        tag='',
        pull_request=None,
        commit='9b1df471879c0caae0594539d0ad87aab06a1ecd',
    )

    actual = get_job_ids(config)
    expected = ([], 'failed')
    assert actual == expected


def test_errors(monkeypatch, caplog):
    """Test handled exceptions."""
    replies = {
        '/projects/user/repo/history?recordsNumber=10': dict(),
        '/projects/user/repo/build/1.6.0.43': dict(),
    }
    monkeypatch.setattr('appveyor_artifacts.query_api', partial(mock_query_api, replies=replies))

    config = dict(
        owner='user',
        repo='repo',
        tag='',
        pull_request=None,
        commit='9b1df471879c0caae0594539d0ad87aab06a1ecd',
    )

    with pytest.raises(HandledError):
        get_job_ids(config)
    assert caplog.records()[-2].message == 'Bad JSON reply: "builds" key missing.'

    replies['/projects/user/repo/history?recordsNumber=10']['builds'] = [
        {'branch': 'master', 'commitId': '9b1df471879c0caae0594539d0ad87aab06a1ecd', 'isTag': False, 'jobs': [],
         'status': 'success', 'version': '1.6.0.43'},
    ]

    with pytest.raises(HandledError):
        get_job_ids(config)
    assert caplog.records()[-2].message == 'Bad JSON reply: "build" key missing.'

    replies['/projects/user/repo/build/1.6.0.43']['build'] = dict()

    with pytest.raises(HandledError):
        get_job_ids(config)
    assert caplog.records()[-2].message == 'Bad JSON reply: "jobs" key missing.'

    replies['/projects/user/repo/build/1.6.0.43']['build']['jobs'] = [{'jobId': 'spfxkimxcj6faq57'}]
    assert get_job_ids(config) == (['spfxkimxcj6faq57'], 'success')
