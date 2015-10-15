"""Download artifacts from AppVeyor builds of the same commit/pull request.

This tool is mainly used to download a ".coverage" file from AppVeyor to
combine it with the one in Travis (since Coveralls doesn't support multi-ci
code coverage). However this can be used to download any artifact from an
AppVeyor project.

TODO:
1) --mangle-coverage
4) Handle master, feature, tag, pull request.
5) handle re-running old build, get latest.
6) --out-dir
7) http://www.appveyor.com/docs/api/samples/download-artifacts-ps
8) --time-out
9) Tox tests on travis should test real-world. Get these files and md5 compare.

https://github.com/Robpol86/appveyor-artifacts
https://pypi.python.org/pypi/appveyor-artifacts

Usage:
    appveyor-artifacts [options] download
    appveyor-artifacts -h | --help
    appveyor-artifacts -V | --version

Options:
    -c SHA --commit=SHA         Git commit currently building.
    -h --help                   Show this screen.
    -o NAME --owner-name=NAME   Repository owner/account name
    -p NUM --pull-request=NUM   Pull request number of current job.
    -r NAME --repo-name=NAME    Repository name.
    -t NAME --tag-name=NAME     Tag name that triggered current job.
    -v --verbose                Raise exceptions with tracebacks.
    -V --version                Print appveyor-artifacts version.
"""

import functools
import logging
import os
import re
import signal
import sys

import pkg_resources
import requests
import requests.exceptions
from docopt import docopt

API_PREFIX = 'https://ci.appveyor.com/api'
REGEX_COMMIT = re.compile(r'^[0-9a-f]{7,40}$')
REGEX_NAME = re.compile(r'^[0-9a-zA-Z\._-]+$')


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


def get_arguments(argv=None, environ=None):
    """Get command line arguments or values from environment variables.

    :param list argv: Command line argument list to process. For testing.
    :param dict environ: Environment variables. For testing.

    :return: Parsed options.
    :rtype: dict
    """
    name = 'appveyor-artifacts'
    environ = environ or os.environ
    require = getattr(pkg_resources, 'require')  # Stupid linting error.
    commit, owner, pull_request, repo, tag = '', '', '', '', ''

    # Run docopt.
    project = [p for p in require(name) if p.project_name == name][0]
    version = project.version
    args = docopt(__doc__, argv=argv or sys.argv[1:], version=version)

    # Handle Travis environment variables.
    if environ.get('TRAVIS') == 'true':
        commit = environ.get('TRAVIS_COMMIT', '')
        owner = environ.get('TRAVIS_REPO_SLUG', '/').split('/')[0]
        pull_request = environ.get('TRAVIS_PULL_REQUEST', '')
        repo = environ.get('TRAVIS_REPO_SLUG', '/').split('/')[1]
        tag = environ.get('TRAVIS_TAG', '')

    # Command line arguments override.
    commit = args['--commit'] or commit
    owner = args['--owner-name'] or owner
    pull_request = args['--pull-request'] or pull_request
    repo = args['--repo-name'] or repo
    tag = args['--tag-name'] or tag

    # Convert pull_request.
    try:
        pull_request = int(pull_request)
    except (TypeError, ValueError):
        pull_request = None

    # Merge env variables and have command line args override.
    config = dict(commit=commit, owner=owner, pull_request=pull_request, repo=repo, tag=tag, verbose=args['--verbose'])

    return config


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
    # Validate config.
    if not config['commit'] or not REGEX_COMMIT.match(config['commit']):
        log.error('No or invalid git commit obtained.')
        raise HandledError
    if not config['owner'] or not REGEX_NAME.match(config['owner']):
        log.error('No or invalid repo owner name obtained.')
        raise HandledError
    if not config['repo'] or not REGEX_NAME.match(config['repo']):
        log.error('No or invalid repo name obtained.')
        raise HandledError


def entry_point():
    """Entry-point from setuptools."""
    signal.signal(signal.SIGINT, lambda *_: getattr(os, '_exit')(0))  # Properly handle Control+C
    config = get_arguments()
    setup_logging(config['verbose'])
    try:
        main(config)
    except HandledError:
        logging.critical('Failure.')
        sys.exit(1)


if __name__ == '__main__':
    entry_point()
