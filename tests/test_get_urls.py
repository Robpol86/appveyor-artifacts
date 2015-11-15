"""Test get_urls() function."""

import py
import pytest

from appveyor_artifacts import API_PREFIX, get_urls, HandledError

PREFIX = API_PREFIX + '/buildjobs/%s/artifacts/%s'


@pytest.mark.parametrize('artifacts', [True, False])
def test_instant_success(monkeypatch, artifacts):
    """Test successful run with no waiting.

    :param monkeypatch: pytest fixture.
    :param bool artifacts: If simulation should have or lack artifacts.
    """
    monkeypatch.setattr('appveyor_artifacts.query_build_version', lambda _: '1.0.1')
    monkeypatch.setattr('appveyor_artifacts.query_job_ids', lambda *_: [('abc1def2ghi3jkl4', 'success')])
    monkeypatch.setattr('appveyor_artifacts.query_artifacts',
                        lambda _: [('abc1def2ghi3jkl4', 'README.md', 1234)] if artifacts else [])

    config = dict(always_job_dirs=False, no_job_dirs=None, dir=None)
    actual = get_urls(config)
    expected = {py.path.local('README.md'): (PREFIX % ('abc1def2ghi3jkl4', 'README.md'), 1234)} if artifacts else dict()
    assert actual == expected


@pytest.mark.parametrize('timeout', [True, False])
def test_wait_for_job_queue(monkeypatch, caplog, timeout):
    """Test timeout and delayed job queue.

    :param monkeypatch: pytest fixture.
    :param caplog: pytest extension fixture.
    :param bool timeout: Simulate timeout scenario.
    """
    answers = [None, '1.0.1']
    monkeypatch.setattr('appveyor_artifacts.SLEEP_FOR', 0.01)
    monkeypatch.setattr('appveyor_artifacts.query_build_version', lambda _: None if timeout else answers.pop(0))
    monkeypatch.setattr('appveyor_artifacts.query_job_ids', lambda *_: [('abc1def2ghi3jkl4', 'success')])
    monkeypatch.setattr('appveyor_artifacts.query_artifacts', lambda _: list())

    if timeout:
        with pytest.raises(HandledError):
            get_urls(dict())
    else:
        get_urls(dict(always_job_dirs=False, no_job_dirs=None, dir=None))

    messages = [r.message for r in caplog.records if r.levelname != 'DEBUG']
    if timeout:
        assert messages.count('Waiting for job to be queued...') == 3
        assert messages[-1] == 'Timed out waiting for job to be queued or build not found.'
    else:
        assert messages.count('Waiting for job to be queued...') == 1
        assert messages[-1] == 'Found 0 artifacts.'
        assert not answers


@pytest.mark.parametrize('success', [True, False, None])
def test_queued_running_success_or_failed(monkeypatch, caplog, success):
    """Test main while loop with valid job statuses.

    :param monkeypatch: pytest fixture.
    :param caplog: pytest extension fixture.
    :param bool success: If job is successful.
    """
    answers = (['bad'] if success is None else []) + ['queued', 'running'] + (['success'] if success else ['failed'])
    monkeypatch.setattr('appveyor_artifacts.SLEEP_FOR', 0.01)
    monkeypatch.setattr('appveyor_artifacts.query_build_version', lambda _: '1.0.1')
    monkeypatch.setattr('appveyor_artifacts.query_job_ids', lambda *_: [('abc1def2ghi3jkl4', answers.pop(0))])
    monkeypatch.setattr('appveyor_artifacts.query_artifacts', lambda _: [('abc1def2ghi3jkl4', 'README.md', 1234)])

    config = dict(always_job_dirs=False, no_job_dirs=None, dir=None, owner='me', repo='project')
    if not success:
        with pytest.raises(HandledError):
            get_urls(config)
    else:
        get_urls(config)

    messages = [r.message for r in caplog.records if r.levelname != 'DEBUG']
    if success is None:
        expected = ['Got unknown status from AppVeyor API: bad']
    elif success is False:
        expected = [
            'Waiting for all jobs to start...',
            'Waiting for job to finish...',
            'AppVeyor job failed: https://ci.appveyor.com/project/me/project/build/job/abc1def2ghi3jkl4',
        ]
    else:
        expected = [
            'Waiting for all jobs to start...',
            'Waiting for job to finish...',
            'Build successful. Found 1 job.',
            'Found 1 artifact.',
        ]
    assert messages == expected
