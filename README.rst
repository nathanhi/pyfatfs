.. image:: https://img.shields.io/github/actions/workflow/status/nathanhi/pyfatfs/test.yml?style=flat-square
    :target: https://github.com/nathanhi/pyfatfs/actions/workflows/test.yml
    :alt: CI build status
.. image:: https://img.shields.io/readthedocs/pyfatfs?style=flat-square
    :target: https://pyfatfs.readthedocs.io/
    :alt: Read the Docs
.. image:: https://img.shields.io/coveralls/github/nathanhi/pyfatfs?style=flat-square
    :target: https://coveralls.io/github/nathanhi/pyfatfs
    :alt: Test coverage overview
.. image:: https://img.shields.io/codacy/grade/3def4d7b0bcd4b6f9aa4bb64e0338540?style=flat-square
    :target: https://app.codacy.com/gh/nathanhi/pyfatfs
    :alt: Codacy Code Quality
.. image:: https://img.shields.io/pypi/pyversions/pyfatfs?style=flat-square
    :target: https://github.com/nathanhi/pyfatfs
    :alt: PyPI - Python Version
.. image:: https://img.shields.io/pypi/v/pyfatfs?style=flat-square
    :target: https://pypi.org/project/pyfatfs
    :alt: PyPI
.. image:: https://img.shields.io/github/license/nathanhi/pyfatfs.svg?style=flat-square
    :target: https://github.com/nathanhi/pyfatfs/blob/HEAD/LICENSE
    :alt: MIT License

pyfatfs
=======

pyfatfs is a filesystem module for use with `PyFilesystem2 <https://pypi.org/project/fs/>`_
for anyone who needs to access or modify files on a FAT filesystem. It also
provides a low-level API that allows direct interaction with a FAT filesystem
without PyFilesystem2 abstraction.

pyfatfs supports FAT12/FAT16/FAT32 as well as the VFAT extension (long file names).

Installation
------------

pyfatfs is available via PyPI as ``pyfatfs``, so just execute the following
command to install the package for your project:

.. code-block:: bash

   $ pip install pyfatfs


Usage
=====

The easiest way to get started with pyfatfs is to use it in conjunction
with PyFilesystem2:

PyFilesystem2
-------------

.. pyfilesystem-quickstart-begin

Use fs.open_fs to open a filesystem with a FAT `FS URL <https://pyfilesystem2.readthedocs.io/en/latest/openers.html>`_:

.. code-block:: python

   import fs
   my_fs = fs.open_fs("fat:///dev/sda1")


Parameters
''''''''''

It is possible to supply query parameters to the URI of the
PyFilesystem2 opener to influence certain behavior; it can
be compared to mount options. Multiple parameters can be
supplied by separating them via ``ampersand (&)``.

encoding
^^^^^^^^

pyfatfs offers an encoding parameter to allow overriding the
default encoding of ibm437 for file names, which was mainly
used by DOS and still is the `default on Linux <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/fs/fat/Kconfig?h=v5.10#n81>`_.

Any encoding known by Python can be used as value for this
parameter, but keep in mind that this might affect interoperability
with other systems, especially when the selected encoding/codepage
is not native or supported.

Please note that this only affects encoding of the 8DOT3 short file names, not
long file names of the VFAT extension, as LFN are always stored as UTF-16-LE.

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
created files that do not match the 8DOT3 rules. This defaults to ``true``
but can be disabled by setting preserve_case to ``false``:

.. code-block:: python

   import fs
   my_fs = fs.open_fs("fat:///dev/sda1?preserve_case=false")


read_only
^^^^^^^^^

Open filesystem in read-only mode and thus don't allow writes/modifications.
This defaults to false but can be enabled by setting read_only to ``true``:

.. code-block:: python

   import fs
   my_fs = fs.open_fs("fat:///dev/sda1?read_only=true")


utc
^^^

Create all timestamps on the filesystem in UTC time rather than local time.
Affects all directory entries' creation, modification and access times.

.. code-block:: python

    import fs
    my_fs = fs.open_fs("fat:///dev/sda1?utc=true")


lazy_load
^^^^^^^^^

If set to ``true`` (default), the directory entries are loaded only when accessed
to increase performance with larger filesystems and resilience against
recursion / directory loops.

.. code-block:: python

    import fs
    my_fs = fs.open_fs("fat:///dev/sda1?lazy_load=false")
.. pyfilesystem-quickstart-end

Testing
-------

Tests are located at the `tests` directory. In order to test your new
contribution to pyfatfs just run

.. code-block:: bash

    $ python setup.py test

from your shell.
