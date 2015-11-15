"""Test query_job_ids()."""

from functools import partial

import pytest

from appveyor_artifacts import HandledError, query_job_ids


def mock_query_api(url, replies):
    """Mock JSON replies.

    :param str url: Url as key.
    :param dict replies: Mock replies from test functions.
    """
    return replies[url]


def test_no_name(monkeypatch):
    """Test success workflow with nameless job (e.g. when using tox).

    :param monkeypatch: pytest fixture.
    """
    replies = {
        '/projects/Robpol86/terminaltables/build/1.0.239': dict(build=dict(jobs=[
            {'jobId': 'ocw0l628ww5yqqxy', 'name': '', 'status': 'success'},
        ])),
    }
    monkeypatch.setattr('appveyor_artifacts.query_api', partial(mock_query_api, replies=replies))

    build_version = '1.0.239'
    config = dict(job_name='', owner='Robpol86', repo='terminaltables')

    actual = query_job_ids(build_version, config)
    expected = [('ocw0l628ww5yqqxy', 'success')]
    assert actual == expected


@pytest.mark.parametrize('job_name', ['', r'Environment: PYTHON=C:\Python34-x64'])
def test_multiple_jobs(monkeypatch, caplog, job_name):
    """Test success workflow with a multi-job build.

    :param monkeypatch: pytest fixture.
    :param caplog: pytest extension fixture.
    :param str job_name: AppVeyor job name to test against.
    """
    replies = {
        '/projects/Robpol86/flask-statics-helper/build/1.0.9': dict(build=dict(jobs=[
            {'jobId': 'ahj8kvyf8ewsqkqv', 'name': 'Environment: PYTHON=C:\\Python27', 'status': 'success'},
            {'jobId': 'a06o6tnx6fjn5kua', 'name': 'Environment: PYTHON=C:\\Python27-x64', 'status': 'running'},
            {'jobId': 'xp1sqi838e4h98p2', 'name': 'Environment: PYTHON=C:\\Python33', 'status': 'queued'},
            {'jobId': 'b3mbow7ymelmxbwe', 'name': 'Environment: PYTHON=C:\\Python33-x64', 'status': 'failed'},
            {'jobId': 'nw8fff3v4ujsvcu1', 'name': 'Environment: PYTHON=C:\\Python34', 'status': 'running'},
            {'jobId': 'tlufgeiwhnds036d', 'name': 'Environment: PYTHON=C:\\Python34-x64', 'status': 'success'},
        ])),
    }
    monkeypatch.setattr('appveyor_artifacts.query_api', partial(mock_query_api, replies=replies))

    build_version = '1.0.9'
    config = dict(job_name=job_name, owner='Robpol86', repo='flask-statics-helper')

    actual = query_job_ids(build_version, config)
    if job_name:
        expected = [('tlufgeiwhnds036d', 'success')]
    else:
        expected = [
            ('ahj8kvyf8ewsqkqv', 'success'),
            ('a06o6tnx6fjn5kua', 'running'),
            ('xp1sqi838e4h98p2', 'queued'),
            ('b3mbow7ymelmxbwe', 'failed'),
            ('nw8fff3v4ujsvcu1', 'running'),
            ('tlufgeiwhnds036d', 'success'),
        ]
    assert actual == expected

    messages = [r.message for r in caplog.records]
    if job_name:
        assert messages[-2] == 'Filtering by job name: found match!'
    else:
        assert 'Filtering by job name: found match!' not in messages


def test_errors(monkeypatch, caplog):
    """Test handled exceptions.

    :param monkeypatch: pytest fixture.
    :param caplog: pytest extension fixture.
    """
    replies = {
        '/projects/user/repo/build/1.6.0.43': dict(),
    }
    monkeypatch.setattr('appveyor_artifacts.query_api', partial(mock_query_api, replies=replies))

    build_version = '1.6.0.43'
    config = dict(job_name='unknown', owner='user', repo='repo')

    with pytest.raises(HandledError):
        query_job_ids(build_version, config)
    assert caplog.records[-2].message == 'Bad JSON reply: "build" key missing.'

    replies['/projects/user/repo/build/1.6.0.43']['build'] = dict()
    with pytest.raises(HandledError):
        query_job_ids(build_version, config)
    assert caplog.records[-2].message == 'Bad JSON reply: "jobs" key missing.'

    replies['/projects/user/repo/build/1.6.0.43']['build']['jobs'] = [
        {'jobId': 'spfxkimxcj6faq57', 'name': '', 'status': 'success'}
    ]
    with pytest.raises(HandledError):
        query_job_ids(build_version, config)
    assert caplog.records[-2].message == 'Job name "unknown" not found.'

    config['job_name'] = ''
    assert query_job_ids(build_version, config) == [('spfxkimxcj6faq57', 'success')]
