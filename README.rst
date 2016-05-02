==================
appveyor-artifacts
==================

Download artifacts from AppVeyor builds of the same commit/pull request.

Supports editing/mangling Python coverage files so you can merge coverage files generated on AppVeyor/Windows with those
generated on Linux/OSX/Travis.

* Python 2.7, PyPy, PyPy3, 3.3, 3.4, and 3.5 supported on Linux and OS X.

.. image:: https://img.shields.io/appveyor/ci/Robpol86/appveyor-artifacts/master.svg?style=flat-square&label=AppVeyor%20CI
    :target: https://ci.appveyor.com/project/Robpol86/appveyor-artifacts
    :alt: Build Status Windows

.. image:: https://img.shields.io/travis/Robpol86/appveyor-artifacts/master.svg?style=flat-square&label=Travis%20CI
    :target: https://travis-ci.org/Robpol86/appveyor-artifacts
    :alt: Build Status

.. image:: https://img.shields.io/coveralls/Robpol86/appveyor-artifacts/master.svg?style=flat-square&label=Coveralls
    :target: https://coveralls.io/github/Robpol86/appveyor-artifacts
    :alt: Coverage Status

.. image:: https://img.shields.io/pypi/v/appveyor-artifacts.svg?style=flat-square&label=Latest
    :target: https://pypi.python.org/pypi/appveyor-artifacts
    :alt: Latest Version

.. image:: https://img.shields.io/pypi/dm/appveyor-artifacts.svg?style=flat-square&label=PyPI%20Downloads
    :target: https://pypi.python.org/pypi/appveyor-artifacts
    :alt: Downloads

Quickstart
==========

Install and run:

.. code:: bash

    pip install appveyor-artifacts
    appveyor-artifacts --help

Example
=======

Example usage in Travis CI yaml file:

.. code:: yaml

    after_success:
      - mv .coverage .coverage.travis
      - appveyor-artifacts -m download
      - coverage combine
      - coveralls

And in AppVeyor CI yaml file:

.. code:: yaml

    artifacts:
      - path: .coverage

Changelog
=========

This project adheres to `Semantic Versioning <http://semver.org/>`_.

1.0.2 - 2016-05-01
------------------

Fixed
    * Handling ConnectionError exceptions.
    * UnicodeDecodeError on Python 3.x when reading binary files.
    * Retrying up to two times per API call on network errors.

1.0.1 - 2015-11-30
------------------

Fixed
    * Subdirectory handling.

1.0.0 - 2015-11-02
------------------

* Initial release.
