pyfat
=====

.. image:: https://img.shields.io/travis/nathanhi/pyfat.svg?maxAge=2592000&style=flat-square&branch=wip
    :target: https://travis-ci.org/nathanhi/pyfat
    :alt: CI build status
.. image:: https://img.shields.io/coveralls/nathanhi/pyfat.svg?maxAge=2592000&style=flat-square
    :target: https://coveralls.io/github/nathanhi/pyfat
    :alt: Test coverage overview
.. image:: https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8-blue?style=flat-square
    :target: https://github.com/nathanhi/pyfat
    :alt: Python compatibility matrix
.. image:: https://img.shields.io/github/license/nathanhi/pyfat.svg?maxAge=2592000&style=flat-square
    :target: https://github.com/nathanhi/pyfat/blob/HEAD/LICENSE
    :alt: MIT License

pyfat is a filesystem module for use with PyFilesystem2 for anyone
who needs to access or modify files on a FAT filesystem.

pyfat supports FAT12/16/32 as well as the VFAT extension (long file names).


Installation
------------

To install pyfat just run from the root of the project:

.. code-block:: bash

    $ python setup.py install


Usage
=====
Opener
------

Use fs.open_fs to open a filesystem with a FAT `FS URL <https://pyfilesystem2.readthedocs.io/en/latest/openers.html>`_:

.. code-block:: python

    import fs
    my_fs = fs.open_fs("fat:///dev/sda1")

The following URL parameters are supported: encoding and offset

Parameters
''''''''''

encoding
^^^^^^^^

pyfat offers an encoding parameter to allow overriding the default encoding
of ibm437 for file names, which was mainly used by DOS and still is a
fallback of Linux.

Later versions of Windows were using Windows-1252, also known as CP1252, as
encoding. Any encoding known by Python can be used as value for this parameter.

.. code-block:: python

    import fs
    my_fs = fs.open_fs("fat:///dev/sda1?encoding=cp1252")


offset
^^^^^^

Specify an offset in bytes to skip when accessing the file. That way even
complete disk images can be read if the location of the partition is known:

.. code-block:: python

    import fs
    my_fs = fs.open_fs("fat:///dev/sda?offset=32256")


preserve_case
^^^^^^^^^^^^^

Preserve case when creating files. This will force LFN entries for all
created files that do not match the 8DOT3 rules. This defaults to true
but can be disabled by setting preserve_case to false:

.. code-block:: python

    import fs
    my_fs = fs.open_fs("fat:///dev/sda1?preserve_case=false")


Testing
-------

Tests are located at the `tests` directory. In order to test your new
contribution to pyfat just run

.. code-block:: bash

    $ python setup.py test

from your shell.


Contribute
----------

Feel free to contribute improvements to this package via mail or pull request.

The preferred method of development is a test driven approach and following
the nvie git flow branching model. Please be so kind to bear these things in
mind when handing in improvements. Thank you very much.
