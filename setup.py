#!/usr/bin/env python
"""Setup script for the project."""

from __future__ import print_function

import codecs
import os

from setuptools import setup


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
    description='Download artifacts from AppVeyor builds of the same commit/pull request.',
    entry_points={'console_scripts': ['appveyor-artifacts = appveyor_artifacts:entry_point']},
    install_requires=['docopt', 'requests'],
    keywords='appveyor artifacts travis coverage coveralls',
    license='MIT',
    long_description=safe_read('README.rst'),
    name='appveyor-artifacts',
    py_modules=['appveyor_artifacts'],
    url='https://github.com/Robpol86/appveyor-artifacts',
    version='0.0.2',
    zip_safe=True,
)
