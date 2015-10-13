"""Test setup_logging() function."""

import logging
import time

import pytest

from appveyor_artifacts import setup_logging


@pytest.mark.parametrize('verbose', [True, False])
def test_setup_logging(capsys, verbose):
    """Test setup_logging()."""
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
