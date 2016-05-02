#!/usr/bin/env python
r"""Download artifacts from AppVeyor builds of the same commit/pull request.

This tool is mainly used to download a ".coverage" file from AppVeyor to
combine it with the one in Travis (since Coveralls doesn't support multi-ci
code coverage). However this can be used to download any artifact from an
AppVeyor project.

If your project creates multiple jobs for one commit (e.g. different Python
versions, or a matrix in either yaml file), you can use the `--job-name`
option to get artifacts matching your local environment. Example:
appveyor-artifacts --job-name="Environment: PYTHON=C:\Python27" download

https://github.com/Robpol86/appveyor-artifacts
https://pypi.python.org/pypi/appveyor-artifacts

Usage:
    appveyor-artifacts [options] download
    appveyor-artifacts -h | --help
    appveyor-artifacts -V | --version

Options:
    -C DIR --dir=DIR            Download to DIR instead of cwd.
    -c SHA --commit=SHA         Git commit currently building.
    -h --help                   Show this screen.
    -i --ignore-errors          Exit 0 on errors.
    -j --always-job-dirs        Always download files within ./<jobID>/ dirs.
    -J MODE --no-job-dirs=MODE  All jobs download to same directory. Modes for
                                file path collisions: rename, overwrite, skip
    -m --mangle-coverage        Edit downloaded .coverage file(s) replacing
                                Windows paths with Linux paths.
    -n NAME --repo-name=NAME    Repository name.
    -N JOB --job-name=JOB       Filter by job name (Python versions, etc).
    -o NAME --owner-name=NAME   Repository owner/account name.
    -p NUM --pull-request=NUM   Pull request number of current job.
    -r --raise                  Don't handle exceptions, raise all the way.
    -t NAME --tag-name=NAME     Tag name that triggered current job.
    -v --verbose                Raise exceptions with tracebacks.
    -V --version                Print appveyor-artifacts version.
"""

from __future__ import print_function

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

__author__ = '@Robpol86'
__license__ = 'MIT'
__version__ = '1.0.2'

API_PREFIX = 'https://ci.appveyor.com/api'
QUERY_ATTEMPTS = 3
REGEX_COMMIT = re.compile(r'^[0-9a-f]{7,40}$')
REGEX_GENERAL = re.compile(r'^[0-9a-zA-Z\._-]+$')
REGEX_MANGLE = re.compile(r'"(C:\\\\projects\\\\(?:(?!": \[).)+)')  # http://stackoverflow.com/a/17089058/1198943
SLEEP_FOR = 10


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
    if not verbose:
        logging.getLogger('requests').setLevel(logging.WARNING)

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
        """Inject `log` argument into wrapped function.

        :param list args: Pass through all positional arguments.
        :param dict kwargs: Pass through all keyword arguments.
        """
        decorator_logger = logging.getLogger('@with_log')
        decorator_logger.debug('Entering %s() function call.', func.__name__)
        log = kwargs.get('log', logging.getLogger(func.__name__))
        try:
            ret = func(log=log, *args, **kwargs)
        finally:
            decorator_logger.debug('Leaving %s() function call.', func.__name__)
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
        if pull_request == 'false':
            pull_request = ''
        repo = environ.get('TRAVIS_REPO_SLUG', '/').split('/')[1].replace('_', '-')
        tag = environ.get('TRAVIS_TAG', '')

    # Command line arguments override.
    commit = args['--commit'] or commit
    owner = args['--owner-name'] or owner
    pull_request = args['--pull-request'] or pull_request
    repo = args['--repo-name'] or repo
    tag = args['--tag-name'] or tag

    # Merge env variables and have command line args override.
    config = {
        'always_job_dirs': args['--always-job-dirs'],
        'commit': commit,
        'dir': args['--dir'] or '',
        'ignore_errors': args['--ignore-errors'],
        'job_name': args['--job-name'] or '',
        'mangle_coverage': args['--mangle-coverage'],
        'no_job_dirs': args['--no-job-dirs'] or '',
        'owner': owner,
        'pull_request': pull_request,
        'raise': args['--raise'],
        'repo': repo,
        'tag': tag,
        'verbose': args['--verbose'],
    }

    return config


@with_log
def query_api(endpoint, log):
    """Query the AppVeyor API.

    :raise HandledError: On non HTTP200 responses or invalid JSON response.

    :param str endpoint: API endpoint to query (e.g. '/projects/Robpol86/appveyor-artifacts').
    :param logging.Logger log: Logger for this function. Populated by with_log() decorator.

    :return: Parsed JSON response.
    :rtype: dict
    """
    url = API_PREFIX + endpoint
    headers = {'content-type': 'application/json'}
    response = None
    log.debug('Querying %s with headers %s.', url, headers)
    for i in range(QUERY_ATTEMPTS):
        try:
            try:
                response = requests.get(url, headers=headers, timeout=10)
            except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout, requests.Timeout):
                log.error('Timed out waiting for reply from server.')
                raise HandledError
            except requests.ConnectionError:
                log.error('Unable to connect to server.')
                raise HandledError
        except HandledError:
            if i == QUERY_ATTEMPTS - 1:
                raise
            log.warning('Network error, retrying in 1 second...')
            time.sleep(1)
        else:
            break
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
    :param logging.Logger log: Logger for this function. Populated by with_log() decorator.
    """
    if config['always_job_dirs'] and config['no_job_dirs']:
        log.error('Contradiction: --always-job-dirs and --no-job-dirs used.')
        raise HandledError
    if config['commit'] and not REGEX_COMMIT.match(config['commit']):
        log.error('No or invalid git commit obtained.')
        raise HandledError
    if config['dir'] and not os.path.isdir(config['dir']):
        log.error("Not a directory or doesn't exist: %s", config['dir'])
        raise HandledError
    if config['no_job_dirs'] not in ('', 'rename', 'overwrite', 'skip'):
        log.error('--no-job-dirs has invalid value. Check --help for valid values.')
        raise HandledError
    if not config['owner'] or not REGEX_GENERAL.match(config['owner']):
        log.error('No or invalid repo owner name obtained.')
        raise HandledError
    if config['pull_request'] and not config['pull_request'].isdigit():
        log.error('--pull-request is not a digit.')
        raise HandledError
    if not config['repo'] or not REGEX_GENERAL.match(config['repo']):
        log.error('No or invalid repo name obtained.')
        raise HandledError
    if config['tag'] and not REGEX_GENERAL.match(config['tag']):
        log.error('Invalid git tag obtained.')
        raise HandledError


@with_log
def query_build_version(config, log):
    """Find the build version we're looking for.

    AppVeyor calls build IDs "versions" which is confusing but whatever. Job IDs aren't available in the history query,
    only on latest, specific version, and deployment queries. Hence we need two queries to get a one-time status update.

    Returns None if the job isn't queued yet.

    :raise HandledError: On invalid JSON data.

    :param dict config: Dictionary from get_arguments().
    :param logging.Logger log: Logger for this function. Populated by with_log() decorator.

    :return: Build version.
    :rtype: str
    """
    url = '/projects/{0}/{1}/history?recordsNumber=10'.format(config['owner'], config['repo'])

    # Query history.
    log.debug('Querying AppVeyor history API for %s/%s...', config['owner'], config['repo'])
    json_data = query_api(url)
    if 'builds' not in json_data:
        log.error('Bad JSON reply: "builds" key missing.')
        raise HandledError

    # Find AppVeyor build "version".
    for build in json_data['builds']:
        if config['tag'] and config['tag'] == build.get('tag'):
            log.debug('This is a tag build.')
        elif config['pull_request'] and config['pull_request'] == build.get('pullRequestId'):
            log.debug('This is a pull request build.')
        elif config['commit'] == build['commitId']:
            log.debug('This is a branch build.')
        else:
            continue
        log.debug('Build JSON dict: %s', str(build))
        return build['version']
    return None


@with_log
def query_job_ids(build_version, config, log):
    """Get one or more job IDs and their status associated with a build version.

    Filters jobs by name if --job-name is specified.

    :raise HandledError: On invalid JSON data or bad job name.

    :param str build_version: AppVeyor build version from query_build_version().
    :param dict config: Dictionary from get_arguments().
    :param logging.Logger log: Logger for this function. Populated by with_log() decorator.

    :return: List of two-item tuples. Job ID (first) and its status (second).
    :rtype: list
    """
    url = '/projects/{0}/{1}/build/{2}'.format(config['owner'], config['repo'], build_version)

    # Query version.
    log.debug('Querying AppVeyor version API for %s/%s at %s...', config['owner'], config['repo'], build_version)
    json_data = query_api(url)
    if 'build' not in json_data:
        log.error('Bad JSON reply: "build" key missing.')
        raise HandledError
    if 'jobs' not in json_data['build']:
        log.error('Bad JSON reply: "jobs" key missing.')
        raise HandledError

    # Find AppVeyor job.
    all_jobs = list()
    for job in json_data['build']['jobs']:
        if config['job_name'] and config['job_name'] == job['name']:
            log.debug('Filtering by job name: found match!')
            return [(job['jobId'], job['status'])]
        all_jobs.append((job['jobId'], job['status']))
    if config['job_name']:
        log.error('Job name "%s" not found.', config['job_name'])
        raise HandledError
    return all_jobs


@with_log
def query_artifacts(job_ids, log):
    """Query API again for artifacts.

    :param iter job_ids: List of AppVeyor jobIDs.
    :param logging.Logger log: Logger for this function. Populated by with_log() decorator.

    :return: List of tuples: (job ID, artifact file name, artifact file size).
    :rtype: list
    """
    jobs_artifacts = list()
    for job in job_ids:
        url = '/buildjobs/{0}/artifacts'.format(job)
        log.debug('Querying AppVeyor artifact API for %s...', job)
        json_data = query_api(url)
        for artifact in json_data:
            jobs_artifacts.append((job, artifact['fileName'], artifact['size']))
    return jobs_artifacts


@with_log
def artifacts_urls(config, jobs_artifacts, log):
    """Determine destination file paths for job artifacts.

    :param dict config: Dictionary from get_arguments().
    :param iter jobs_artifacts: List of job artifacts from query_artifacts().
    :param logging.Logger log: Logger for this function. Populated by with_log() decorator.

    :return: Destination file paths (keys), download URLs (value[0]), and expected file size (value[1]).
    :rtype: dict
    """
    artifacts = dict()

    # Determine if we should create job ID directories.
    if config['always_job_dirs']:
        job_dirs = True
    elif config['no_job_dirs']:
        job_dirs = False
    elif len(set(i[0] for i in jobs_artifacts)) == 1:
        log.debug('Only one job ID, automatically setting job_dirs = False.')
        job_dirs = False
    elif len(set(i[1] for i in jobs_artifacts)) == len(jobs_artifacts):
        log.debug('No local file conflicts, automatically setting job_dirs = False')
        job_dirs = False
    else:
        log.debug('Multiple job IDs with file conflicts, automatically setting job_dirs = True')
        job_dirs = True

    # Get final URLs and destination file paths.
    root_dir = config['dir'] or os.getcwd()
    for job, file_name, size in jobs_artifacts:
        artifact_url = '{0}/buildjobs/{1}/artifacts/{2}'.format(API_PREFIX, job, file_name)
        artifact_local = os.path.join(root_dir, job if job_dirs else '', file_name)
        if artifact_local in artifacts:
            if config['no_job_dirs'] == 'skip':
                log.debug('Skipping %s from %s', artifact_local, artifact_url)
                continue
            if config['no_job_dirs'] == 'rename':
                new_name = artifact_local
                while new_name in artifacts:
                    path, ext = os.path.splitext(new_name)
                    new_name = (path + '_' + ext) if ext else (new_name + '_')
                log.debug('Renaming %s to %s from %s', artifact_local, new_name, artifact_url)
                artifact_local = new_name
            elif config['no_job_dirs'] == 'overwrite':
                log.debug('Overwriting %s from %s with %s', artifact_local, artifacts[artifact_local][0], artifact_url)
            else:
                log.error('Collision: %s from %s and %s', artifact_local, artifacts[artifact_local][0], artifact_url)
                raise HandledError
        artifacts[artifact_local] = (artifact_url, size)

    return artifacts


@with_log
def get_urls(config, log):
    """Wait for AppVeyor job to finish and get all artifacts' URLs.

    :param dict config: Dictionary from get_arguments().
    :param logging.Logger log: Logger for this function. Populated by with_log() decorator.

    :return: Paths and URLs from artifacts_urls.
    :rtype: dict
    """
    # Wait for job to be queued. Once it is we'll have the "version".
    build_version = None
    for _ in range(3):
        build_version = query_build_version(config)
        if build_version:
            break
        log.info('Waiting for job to be queued...')
        time.sleep(SLEEP_FOR)
    if not build_version:
        log.error('Timed out waiting for job to be queued or build not found.')
        raise HandledError

    # Get job IDs. Wait for AppVeyor job to finish.
    job_ids = list()
    valid_statuses = ['success', 'failed', 'running', 'queued']
    while True:
        job_ids = query_job_ids(build_version, config)
        statuses = set([i[1] for i in job_ids])
        if 'failed' in statuses:
            job = [i[0] for i in job_ids if i[1] == 'failed'][0]
            url = 'https://ci.appveyor.com/project/{0}/{1}/build/job/{2}'.format(config['owner'], config['repo'], job)
            log.error('AppVeyor job failed: %s', url)
            raise HandledError
        if statuses == set(valid_statuses[:1]):
            log.info('Build successful. Found %d job%s.', len(job_ids), '' if len(job_ids) == 1 else 's')
            break
        if 'running' in statuses:
            log.info('Waiting for job%s to finish...', '' if len(job_ids) == 1 else 's')
        elif 'queued' in statuses:
            log.info('Waiting for all jobs to start...')
        else:
            log.error('Got unknown status from AppVeyor API: %s', ' '.join(statuses - set(valid_statuses)))
            raise HandledError
        time.sleep(SLEEP_FOR)

    # Get artifacts.
    artifacts = query_artifacts([i[0] for i in job_ids])
    log.info('Found %d artifact%s.', len(artifacts), '' if len(artifacts) == 1 else 's')
    return artifacts_urls(config, artifacts) if artifacts else dict()


@with_log
def download_file(config, local_path, url, expected_size, chunk_size, log):
    """Download a file.

    :param dict config: Dictionary from get_arguments().
    :param str local_path: Destination path to save file to.
    :param str url: URL of the file to download.
    :param int expected_size: Expected file size in bytes.
    :param int chunk_size: Number of bytes to read in memory before writing to disk and printing a dot.
    :param logging.Logger log: Logger for this function. Populated by with_log() decorator.
    """
    if not os.path.exists(os.path.dirname(local_path)):
        log.debug('Creating directory: %s', os.path.dirname(local_path))
        os.makedirs(os.path.dirname(local_path))
    if os.path.exists(local_path):
        log.error('File already exists: %s', local_path)
        raise HandledError
    relative_path = os.path.relpath(local_path, config['dir'] or os.getcwd())
    print(' => {0}'.format(relative_path), end=' ', file=sys.stderr)

    # Download file.
    log.debug('Writing to: %s', local_path)
    with open(local_path, 'wb') as handle:
        response = requests.get(url, stream=True)
        for chunk in response.iter_content(chunk_size):
            handle.write(chunk)
            print('.', end='', file=sys.stderr)

    file_size = os.path.getsize(local_path)
    print(' {0} bytes'.format(file_size), file=sys.stderr)
    if file_size != expected_size:
        log.error('Expected %d bytes but got %d bytes instead.', expected_size, file_size)
        raise HandledError


@with_log
def mangle_coverage(local_path, log):
    """Edit .coverage file substituting Windows file paths to Linux paths.

    :param str local_path: Destination path to save file to.
    :param logging.Logger log: Logger for this function. Populated by with_log() decorator.
    """
    # Read the file, or return if not a .coverage file.
    with open(local_path, mode='rb') as handle:
        if handle.read(13) != b'!coverage.py:':
            log.debug('File %s not a coverage file.', local_path)
            return
        handle.seek(0)

        # I'm lazy, reading all of this into memory. What could possibly go wrong?
        file_contents = handle.read(52428800).decode('utf-8')  # 50 MiB limit, surely this is enough?

    # Substitute paths.
    for windows_path in set(REGEX_MANGLE.findall(file_contents)):
        unix_relative_path = windows_path.replace(r'\\', '/').split('/', 3)[-1]
        unix_absolute_path = os.path.abspath(unix_relative_path)
        if not os.path.isfile(unix_absolute_path):
            log.debug('Windows path: %s', windows_path)
            log.debug('Unix relative path: %s', unix_relative_path)
            log.error('No such file: %s', unix_absolute_path)
            raise HandledError
        file_contents = file_contents.replace(windows_path, unix_absolute_path)

    # Write.
    with open(local_path, 'w') as handle:
        handle.write(file_contents)


@with_log
def main(config, log):
    """Main function. Runs the program.

    :param dict config: Dictionary from get_arguments().
    :param logging.Logger log: Logger for this function. Populated by with_log() decorator.
    """
    validate(config)
    paths_and_urls = get_urls(config)
    if not paths_and_urls:
        log.warning('No artifacts; nothing to download.')
        return

    # Download files.
    total_size = 0
    chunk_size = max(min(max(v[1] for v in paths_and_urls.values()) // 50, 1048576), 1024)
    log.info('Downloading file%s (1 dot ~ %d KiB):', '' if len(paths_and_urls) == 1 else 's', chunk_size // 1024)
    for size, local_path, url in sorted((v[1], k, v[0]) for k, v in paths_and_urls.items()):
        download_file(config, local_path, url, size, chunk_size)
        total_size += size
        if config['mangle_coverage']:
            mangle_coverage(local_path)

    log.info('Downloaded %d file(s), %d bytes total.', len(paths_and_urls), total_size)


def entry_point():
    """Entry-point from setuptools."""
    signal.signal(signal.SIGINT, lambda *_: getattr(os, '_exit')(0))  # Properly handle Control+C
    config = get_arguments()
    setup_logging(config['verbose'])
    try:
        main(config)
    except HandledError:
        if config['raise']:
            raise
        logging.critical('Failure.')
        sys.exit(0 if config['ignore_errors'] else 1)


if __name__ == '__main__':
    entry_point()
