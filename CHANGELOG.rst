Changelog
=========

All notable changes to this project will be documented in this file.

The format is inspired by `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

Unreleased_
-----------

1.0.5_ - 2022-04-16
-------------------

Fixed
~~~~~

* `Issue #26 <https://github.com/nathanhi/pyfatfs/issues/26>`_: Fix deserialization of date and time values ({a,c,m}time)

1.0.4_ - 2022-04-15
-------------------

Fixed
-----

* `Issue #24 <https://github.com/nathanhi/pyfatfs/issues/24>`_: Do not reorder directory entries when adding/removing entries in a directory
* `Issue #25 <https://github.com/nathanhi/pyfatfs/issues/25>`_: Properly truncate files when configured for truncating (PyFilesystem2/FatIO)
* Always retain last cluster when truncating a file to 0 bytes
* `Issue #27 <https://github.com/nathanhi/pyfatfs/issues/27>`_: Remove outdated `Not yet properly implemented` hint from setinfo docstring

1.0.3_ - 2022-02-27
-------------------

Fixed
-----

* `Issue #22 <https://github.com/nathanhi/pyfatfs/issues/22>`_: Properly combine date and time `DosDateTime` objects when querying ctime/mtime

1.0.2_ - 2022-02-27
-------------------

Fixed
-----

* `PR #23 <https://github.com/nathanhi/pyfatfs/pull/23>`_: Do not try to write FAT if filesystem has been opened read-only by `@abrasive <https://github.com/abrasive>`_

1.0.1_ - 2022-02-08
-------------------

Fixed
-----

* (mkfs) Handle offset correct in case of multiple partitions.
* (mkfs) `Issue #18 <https://github.com/nathanhi/pyfatfs/issues/18>` Add volume label dir entry
* (mkfs) Fix default size detection

1.0.0_ - 2022-02-03
-------------------

Added
~~~~~

* Static ``new`` method for ``FATDirectoryEntry``
* `PR #17 <https://github.com/nathanhi/pyfatfs/pull/17>`_: ``mkfs`` method by `@wackinger <https://github.com/wackinger>`_ / `@Draegerwerk <https://github.com/Draegerwerk>`_
   * ``FATHeader`` class replaced by ``BootSectorHeader``
   * Initial support of ``FSInfo`` for ``mkfs``
* Expose ``PyFat.set_fp`` function to allow using BytesIO / in-memory files. Provide ``PyFatBytesIOFS`` class for PyFilesystem2

Fixed
~~~~~

* Remove duplicated code
* Properly handle non-ASCII short file names / 8DOT3
* Mark dir/file entries as empty on deletion
* Do not allow creating files when a folder with the same name already exists
* Do not allow creating folders when a file with the same name already exists

Changed
~~~~~~~

* In order to fix non-ASCII short file names, ``FATDirectoryEntry.name``
  is now of ``EightDotThree`` type instead of ``bytes``

Removed
~~~~~~~

* Legacy ``byte_repr()`` function, ``__bytes__()`` is to be used instead
  as a drop-in replacement to serialize FAT and dentry data for writing to
  disk

0.3.1_ - 2021-09-04
-------------------

Fixed
~~~~~

* Fix performance regression on FAT16/32 when serializing a FAT to disk via ``__bytes__``
* Improve performance by only parsing fat size once on open() instead of multiple times

0.3.0_ - 2021-09-04
-------------------

Added
~~~~~

* Support for dirty bit, detects unclean unmounts of a filesystem,
  sets dirty bit on mount and clears it on unmount/close

Deprecated
~~~~~~~~~~

* Implement ``__bytes__()`` instead of ``byte_repr()``,
  it will be removed in 1.0

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

.. _Unreleased: https://github.com/nathanhi/pyfatfs/compare/v1.0.4...HEAD
.. _1.0.4: https://github.com/nathanhi/pyfatfs/compare/v1.0.3...v1.0.4
.. _1.0.3: https://github.com/nathanhi/pyfatfs/compare/v1.0.2...v1.0.3
.. _1.0.2: https://github.com/nathanhi/pyfatfs/compare/v1.0.1...v1.0.2
.. _1.0.1: https://github.com/nathanhi/pyfatfs/compare/v1.0.0...v1.0.1
.. _1.0.0: https://github.com/nathanhi/pyfatfs/compare/v0.3.1...v1.0.0
.. _0.3.1: https://github.com/nathanhi/pyfatfs/compare/v0.3.0...v0.3.1
.. _0.3.0: https://github.com/nathanhi/pyfatfs/compare/v0.2.0...v0.3.0
.. _0.2.0: https://github.com/nathanhi/pyfatfs/compare/v0.1.2...v0.2.0
.. _0.1.2: https://github.com/nathanhi/pyfatfs/compare/v0.1.1...v0.1.2
.. _0.1.1: https://github.com/nathanhi/pyfatfs/compare/v0.1.0...v0.1.1
.. _0.1.0: https://github.com/nathanhi/pyfatfs/releases/tag/v0.1.0
