"""Download artifacts from AppVeyor builds of the same commit/pull request.

This tool is mainly used to download a ".coverage" file from AppVeyor to
combine it with the one in Travis (since Coveralls doesn't support multi-ci
code coverage). However this can be used to download any artifact from an
AppVeyor project.

TODO:
1) --mangle-coverage
2) --account-name
3) --project-slug
4) Handle master, feature, tag, pull request.
5) handle re-running old build, get latest.
6) --out-dir
7) http://www.appveyor.com/docs/api/samples/download-artifacts-ps
8) --time-out
9) Tox tests on travis should test real-world. Get these files and md5 compare.

https://github.com/Robpol86/appveyor_artifacts
https://pypi.python.org/pypi/appveyor_artifacts

Usage:
    appveyor_artifacts [-v] download
    appveyor_artifacts -h | --help
    appveyor_artifacts -V | --version

Options:
    -h --help       Show this screen.
    -v --verbose    Raise exceptions with tracebacks.
    -V --version    Print appveyor_artifacts version.
"""

import functools
import logging
import os
import signal
import sys

import pkg_resources
import requests
import requests.exceptions
from docopt import docopt

API_PREFIX = 'https://ci.appveyor.com/api'


class HandledError(Exception):
    """Generic exception used to signal raise HandledError() in scripts."""

    pass


class InfoFilter(logging.Filter):
    """Filter out non-info and non-debug logging statements.

    From: https://stackoverflow.com/questions/16061641/python-logging-split/16066513#16066513
    """

    def filter(self, record):
        """Filter method.

        :param record: Log record object.

        :return: Keep or ignore this record.
        :rtype: bool
        """
        return record.levelno <= logging.INFO


def setup_logging(verbose=False, logger=None):
    """Setup console logging. Info and below go to stdout, others go to stderr.

    :param bool verbose: Print debug statements.
    :param str logger: Which logger to set handlers to. Used for testing.
    """
    format_ = '%(asctime)s %(levelname)-8s %(name)-40s %(message)s' if verbose else '%(message)s'
    level = logging.DEBUG if verbose else logging.INFO

    handler_stdout = logging.StreamHandler(sys.stdout)
    handler_stdout.setFormatter(logging.Formatter(format_))
    handler_stdout.setLevel(logging.DEBUG)
    handler_stdout.addFilter(InfoFilter())

    handler_stderr = logging.StreamHandler(sys.stderr)
    handler_stderr.setFormatter(logging.Formatter(format_))
    handler_stderr.setLevel(logging.WARNING)

    root_logger = logging.getLogger(logger)
    root_logger.setLevel(level)
    root_logger.addHandler(handler_stdout)
    root_logger.addHandler(handler_stderr)


def with_log(func):
    """Automatically adds a named logger to a function upon function call.

    :param func: Function to decorate.

    :return: Decorated function.
    :rtype: function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Inject `log` argument into wrapped function."""
        decorator_logger = logging.getLogger('@with_log')
        decorator_logger.debug('Entering %s() function call.', func.__name__)
        log = kwargs.get('log', logging.getLogger(func.__name__))
        try:
            ret = func(log=log, *args, **kwargs)
        finally:
            decorator_logger.debug('Exiting %s() function call.', func.__name__)
        return ret
    return wrapper


def get_arguments(doc, argv=None):
    """Get command line arguments.

    :param str doc: Docstring to parse arguments from.
    :param list argv: Command line argument list to process.

    :return: Parsed options.
    :rtype: dict
    """
    name = 'appveyor_artifacts'
    require = getattr(pkg_resources, 'require')  # Stupid linting error.
    project = [p for p in require(name) if p.project_name == name][0]
    version = project.version
    return docopt(doc, argv=argv or sys.argv[1:], version=version)


@with_log
def query_api(endpoint, log):
    """Query the AppVeyor API.

    :raise HandledError: On non HTTP200 responses or invalid JSON response.

    :param str endpoint: API endpoint to query (e.g. '/projects/Robpol86/appveyor-artifacts').

    :return: Parsed JSON response.
    :rtype: dict
    """
    url = API_PREFIX + endpoint
    headers = {'content-type': 'application/json'}
    log.debug('Querying %s with headers %s.', url, headers)
    try:
        response = requests.get(url, headers=headers, timeout=10)
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout, requests.Timeout):
        log.error('Timed out waiting for reply from server.')
        raise HandledError
    log.debug('Response status: %d', response.status_code)
    log.debug('Response headers: %s', str(response.headers))
    log.debug('Response text: %s', response.text)

    if not response.ok:
        message = response.json().get('message')
        if message:
            log.error('HTTP %d: %s', response.status_code, message)
        else:
            log.error('HTTP %d: Unknown error: %s', response.status_code, response.text)
        raise HandledError

    try:
        return response.json()
    except ValueError:
        log.error('Failed to parse JSON: %s', response.text)
        raise HandledError


@with_log
def main(config, log):
    """Todo.

    :param config:
    :return:
    """
    assert config
    assert log


def entry_point():
    """Entry-point from setuptools."""
    signal.signal(signal.SIGINT, lambda *_: getattr(os, '_exit')(0))  # Properly handle Control+C
    config = get_arguments(__doc__)
    setup_logging(config['--verbose'])
    try:
        main(config)
    except HandledError:
        logging.critical('Failure.')
        sys.exit(1)


if __name__ == '__main__':
    entry_point()
