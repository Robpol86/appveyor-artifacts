"""Test setup_logging() function and with_log() decorator."""

import logging
import time

import pytest

from appveyor_artifacts import setup_logging, with_log


@with_log
def log_me(crash, log):
    """Log to logger.

    :param bool crash: Should this raise an exception?
    :param log: logging.getLogger(<name>) return value.
    """
    log.info('Preparing to crash.')
    if crash:
        raise RuntimeError
    log.debug('Crash aborted!')


@pytest.mark.parametrize('verbose', [True, False])
def test_setup_logging(capsys, verbose):
    """Test setup_logging().

    :param capsys: pytest fixture.
    :param bool verbose: Enable verbose logging.
    """
    logger = 'test_logger_{0}'.format(verbose)
    setup_logging(verbose, logger)

    log = logging.getLogger(logger)
    for attr in ('debug', 'info', 'warning', 'error', 'critical'):
        getattr(log, attr)('Test {0}.'.format(attr))
        time.sleep(0.01)
    stdout, stderr = capsys.readouterr()

    if verbose:
        assert logger in stdout
        assert logger in stderr
        assert 'Test debug.' in stdout
    else:
        assert logger not in stdout
        assert logger not in stderr
        assert 'Test debug.' not in stdout
    assert 'Test debug.' not in stderr

    assert 'Test info.' in stdout
    assert 'Test warning.' not in stdout
    assert 'Test error.' not in stdout
    assert 'Test critical.' not in stdout

    assert 'Test info.' not in stderr
    assert 'Test warning.' in stderr
    assert 'Test error.' in stderr
    assert 'Test critical.' in stderr


def test_with_log(caplog):
    """Test with_log() decorator.

    :param caplog: pytest extension fixture.
    """
    # Test crash.
    with pytest.raises(RuntimeError):
        log_me(True)
    records = [(r.levelname, r.message) for r in caplog.records]
    expected = [
        ('DEBUG', 'Entering log_me() function call.'),
        ('INFO', 'Preparing to crash.'),
        ('DEBUG', 'Leaving log_me() function call.'),
    ]
    assert records == expected

    # Test no crash.
    log_me(False)
    records = [(r.levelname, r.message) for r in caplog.records][len(records):]
    expected = [
        ('DEBUG', 'Entering log_me() function call.'),
        ('INFO', 'Preparing to crash.'),
        ('DEBUG', 'Crash aborted!'),
        ('DEBUG', 'Leaving log_me() function call.'),
    ]
    assert records == expected
