"""Download artifacts from AppVeyor builds of the same commit/pull request.

This tool is mainly used to download a ".coverage" file from AppVeyor to
combine it with the one in Travis (since Coveralls doesn't support multi-ci
code coverage). However this can be used to download any artifact from an
AppVeyor project.

TODO:
1) --mangle-coverage
6) --out-dir
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
    -n NAME --repo-name=NAME    Repository name.
    -o NAME --owner-name=NAME   Repository owner/account name.
    -p NUM --pull-request=NUM   Pull request number of current job.
    -r --raise                  Don't handle exceptions, raise all the way.
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
import time

import pkg_resources
import requests
import requests.exceptions
from docopt import docopt

API_PREFIX = 'https://ci.appveyor.com/api'
REGEX_COMMIT = re.compile(r'^[0-9a-f]{7,40}$')
REGEX_GENERAL = re.compile(r'^[0-9a-zA-Z\._-]+$')
SLEEP_FOR = 5


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
    config = dict(
        commit=commit,
        owner=owner,
        pull_request=pull_request,
        repo=repo,
        tag=tag,
        verbose=args['--verbose'],
    )

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
def validate(config, log):
    """Validate config values.

    :raise HandledError: On invalid config values.

    :param dict config: Dictionary from get_arguments().
    """
    if not config['commit'] or not REGEX_COMMIT.match(config['commit']):
        log.error('No or invalid git commit obtained.')
        raise HandledError
    if not config['owner'] or not REGEX_GENERAL.match(config['owner']):
        log.error('No or invalid repo owner name obtained.')
        raise HandledError
    if not config['repo'] or not REGEX_GENERAL.match(config['repo']):
        log.error('No or invalid repo name obtained.')
        raise HandledError
    if config['tag'] and not REGEX_GENERAL.match(config['tag']):
        log.error('Invalid git tag obtained.')
        raise HandledError


@with_log
def get_job_ids(config, log):
    """Issue two queries to AppVeyor's API. One to find the build "version" and another to get the job IDs.

    AppVeyor calls build IDs "versions" which is confusing but whatever. Job IDs aren't available in the history query,
    only on latest, specific version, and deployment queries. Hence we need two queries to get a one-time status update.

    Returns ([], None) if the job isn't queued yet.

    :raise HandledError: On invalid JSON data.

    :param dict config: Dictionary from get_arguments().

    :return: List of AppVeyor jobIDs (first) and the build status (second). Two-item tuple.
    :rtype: tuple
    """
    url = '/projects/{0}/{1}/history?recordsNumber=10'.format(config['owner'], config['repo'])

    # Query history.
    log.debug('Querying AppVeyor history API for %s/%s...', config['owner'], config['repo'])
    json_data = query_api(url)
    if 'builds' not in json_data:
        log.error('Bad JSON reply: "builds" key missing.')
        raise HandledError

    # Find AppVeyor build "version".
    version, status = None, None
    for build in json_data['builds']:
        if config['tag'] and config['tag'] == build.get('tag'):
            log.debug('This is a tag build.')
        elif config['pull_request'] and config['pull_request'] == int(build.get('pullRequestId', 0)):
            log.debug('This is a pull request build.')
        elif config['commit'] == build['commitId']:
            log.debug('This is a branch build.')
        else:
            continue
        log.debug('Build JSON dict: %s', str(build))
        version, status = build['version'], build['status']
        break

    # Return here if build not done yet.
    if status != 'success':
        return list(), status

    # Query version.
    url = '/projects/{0}/{1}/build/{2}'.format(config['owner'], config['repo'], version)
    log.debug('Querying AppVeyor version API for %s/%s at %s...', config['owner'], config['repo'], version)
    json_data = query_api(url)
    if 'build' not in json_data:
        log.error('Bad JSON reply: "build" key missing.')
        raise HandledError
    if 'jobs' not in json_data['build']:
        log.error('Bad JSON reply: "jobs" key missing.')
        raise HandledError

    return [j['jobId'] for j in json_data['build']['jobs']], status


@with_log
def get_artifacts_urls(job_ids, log):
    """Query API again for artifacts' urls.

    :param iter job_ids: List of AppVeyor jobIDs.

    :return: All artifacts' URLs, list of 2-item tuples (job id, url suffix).
    :rtype: list
    """
    artifacts = list()
    for job in job_ids:
        url = '/buildjobs/{0}/artifacts'.format(job)
        log.debug('Querying AppVeyor artifact API for %s/%s at %s...', job)
        json_data = query_api(url)
        for artifact in json_data:
            file_name = artifact['fileName']
            artifacts.append((job, file_name))
    return artifacts


@with_log
def main(config, log):
    """Todo.

    :param config:
    :return:
    """
    validate(config)
    job_ids = list()

    # Get job IDs. Wait for AppVeyor job to finish.
    while True:
        job_ids, status = get_job_ids(config)
        if not status:
            log.info('Waiting for job to be queued...')
        elif status == 'queued':
            log.info('Waiting for job to start...')
        elif status == 'running':
            log.info('Waiting for job to finish...')
        elif status == 'success':
            log.info('Build successful. Found %d job%s.', len(job_ids), '' if len(job_ids) == 1 else 's')
            break
        elif status == 'failed':
            log.error('AppVeyor job failed!')
            raise HandledError
        else:
            log.error('Got unknown status from AppVeyor API: %s', status)
            raise HandledError
        time.sleep(SLEEP_FOR)
    if not job_ids:
        log.error('Status is success but there are no job IDs. BUG!')
        raise HandledError

    # Get artifacts' URLs.
    artifacts = get_artifacts_urls(job_ids)
    log.info('Found %d artifact%s.', len(artifacts), '' if len(artifacts) == 1 else 's')
    if not artifacts:
        log.warning('No artifacts; nothing to download.')
        return


def entry_point():
    """Entry-point from setuptools."""
    signal.signal(signal.SIGINT, lambda *_: getattr(os, '_exit')(0))  # Properly handle Control+C
    config = get_arguments()
    setup_logging(config['verbose'])
    try:
        main(config)
    except HandledError:
        if config['--raise']:
            raise
        logging.critical('Failure.')
        sys.exit(1)


if __name__ == '__main__':
    entry_point()
