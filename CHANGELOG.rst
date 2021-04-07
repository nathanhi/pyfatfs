Changelog
=========

All notable changes to this project will be documented in this file.

The format is inspired by `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

Unreleased_
-----------

0.2.0_ - 2021-04-07
-------------------

Added
~~~~~

* ``readinto`` method to directly read into a bytearray
* Write support for FAT12

Fixed
~~~~~

* Lower required minimum version of PyFilesystem2 to 2.4.0
* Do not fail with ``RemoveRootError`` on ``removetree("/")``
* ``openbin`` now sets the ``b`` mode on file open
* Support non-standard Linux formatted filesystems (i.e. FAT32 with less than 65525 clusters)
   * Emits a warning when such a filesystem is encountered
* Remove check for boot signature version

0.1.2_ - 2021-01-05
-------------------

Fixed
~~~~~

* Fix calculation of FAT entries for FAT12
* `PR #6 <https://github.com/nathanhi/pyfatfs/pull/6>`_: Fix bug in parsing LFNs when opening multiple file systems by `@koolkdev <https://github.com/koolkdev>`_
* `PR #7 <https://github.com/nathanhi/pyfatfs/pull/7>`_: Optimize sequential I/O with big files + small bug fixes in writing/allocating clusters by `@koolkdev <https://github.com/koolkdev>`_
   * Cache known location in filesystem for seek and write operations
   * Fix range check during byte allocation
   * Don't iterate all clusters on write_data_to_cluster

0.1.1_ - 2021-01-04
-------------------

Fixed
~~~~~

* `Issue #4 <https://github.com/nathanhi/pyfatfs/issues/4>`_: Removal of last entry in directory leaves remnants
* `PR #5 <https://github.com/nathanhi/pyfatfs/pull/5>`_: Fix creating directory with name that already conforms to 8DOT3 by `@koolkdev <https://github.com/koolkdev>`_


0.1.0_ - 2021-01-03
-------------------

Initial release of pyfatfs.

Added
~~~~~
* Read-only support for FAT12
* Read-write support for FAT16/32
* Support for long file names (VFAT)
* `PR #1 <https://github.com/nathanhi/pyfatfs/pull/1>`_: Support FAT12/FAT16 disks without extended signature by `@akx <https://github.com/akx>`_
* `PyFilesystem2 <https://pypi.org/project/fs/>`_ opener + API abstraction

Fixed
~~~~~

* `PR #2 <https://github.com/nathanhi/pyfatfs/pull/2>`_: Fix DOS time conversion by `@koolkdev <https://github.com/koolkdev>`_
* `PR #3 <https://github.com/nathanhi/pyfatfs/pull/3>`_: Fix reading from a file and implement arbitrary write by `@koolkdev <https://github.com/koolkdev>`_

.. _Unreleased: https://github.com/nathanhi/pyfatfs/compare/v0.2.0...HEAD
.. _0.2.0: https://github.com/nathanhi/pyfatfs/compare/v0.1.2...v0.2.0
.. _0.1.2: https://github.com/nathanhi/pyfatfs/compare/v0.1.1...v0.1.2
.. _0.1.1: https://github.com/nathanhi/pyfatfs/compare/v0.1.0...v0.1.1
.. _0.1.0: https://github.com/nathanhi/pyfatfs/releases/tag/v0.1.0
