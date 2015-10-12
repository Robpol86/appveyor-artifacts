#!/usr/bin/env python
"""Setup script for the project."""

from __future__ import print_function

import codecs
import os
import sys
from distutils import core

from setuptools import setup


class DumpRequirements(core.Command):
    """Write requirements.txt file for tox."""

    description = 'Write requirements.txt file for tox.'
    user_options = [('outfile=', 'o', 'File path to write to or stderr if "-".')]

    def initialize_options(self):
        """Required by distutils. Using setattr() instead of self. due to PyCharm inspections."""
        setattr(self, 'outfile', None)

    def finalize_options(self):
        """Required by distutils."""
        outfile = os.path.realpath(getattr(self, 'outfile') or 'requirements.txt')
        setattr(self, 'outfile', outfile)

    def run(self):
        """Write to file or standard err (distutils pollutes stdout)."""
        dist = getattr(core, '_setup_distribution')
        requirements = '\n'.join(sorted(set(dist.install_requires + dist.tests_require)))
        outfile = getattr(self, 'outfile')
        if outfile.endswith('-'):
            return print(requirements, file=sys.stderr)
        try:
            with open(outfile, 'w') as handle:
                handle.write(requirements)
        except IOError:
            raise SystemExit('Unable to write to {0}'.format(outfile))
        print('Wrote to {0}'.format(outfile))


def safe_read(path):
    """Try to read file or return empty string if failed.

    :param str path: Relative file path to read.

    :return: File contents.
    :rtype: str
    """
    abspath, file_handle = os.path.join(os.path.abspath(os.path.dirname(__file__)), path), None
    try:
        file_handle = codecs.open(abspath, encoding='utf-8')
        return file_handle.read(131072)
    except IOError:
        return ''
    finally:
        getattr(file_handle, 'close', lambda: None)()


setup(
    author='@Robpol86',
    author_email='robpol86@gmail.com',
    classifiers=[
        'Private :: Do Not Upload',
    ],
    cmdclass=dict(requirements=DumpRequirements),
    description='Download artifacts from AppVeyor builds of the same commit/pull request.',
    install_requires=[],
    keywords='appveyor artifacts travis coverage coveralls',
    license='MIT',
    long_description=safe_read('README.rst'),
    name='appveyor_artifacts',
    py_modules=['appveyor_artifacts'],
    tests_require=['pytest-cov'],
    url='https://github.com/Robpol86/appveyor_artifacts',
    version='0.0.1',
    zip_safe=True,
)