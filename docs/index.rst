fs.fatfs
========

.. automodule:: pyfat

=================
PyFilesystem2 API
=================
.. autoclass:: pyfat.PyFatFS::PyFatFS
   :members:
   :show-inheritance:

================
PyFAT base class
================
.. autoclass:: pyfat.PyFat::PyFat
   :members:

=====================
FAT Directory entries
=====================

Generic directory entries
-------------------------
.. autoclass:: pyfat.FATDirectoryEntry::FATDirectoryEntry
   :members:
   :show-inheritance:

.. autofunction:: pyfat.FATDirectoryEntry.is_8dot3_conform
.. autofunction:: pyfat.FATDirectoryEntry.make_8dot3_name

Long File Name directory entries
--------------------------------
.. autoclass:: pyfat.FATDirectoryEntry::FATLongDirectoryEntry
  :members:
  :show-inheritance:

.. autofunction:: pyfat.FATDirectoryEntry.make_lfn_entry

==========
Exceptions
==========
.. autoexception:: pyfat._exceptions::PyFATException
   :members:
   :show-inheritance:
.. autoexception:: pyfat._exceptions::NotAnLFNEntryException
   :members:
   :show-inheritance:

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
