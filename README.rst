fs.fat
======

.. image:: https://img.shields.io/travis/Draegerwerk/fs.fat/master.svg?style=flat&maxAge=300
    :target: https://travis-ci.org/Draegerwerk/fs.fat
    :alt: ci build status

fs.fat is a filesystem module for use with PyFilesystem2 for anyone
who needs to access or modify files on a FAT filesystem.

fs.fat supports FAT12/16/32 as well as the VFAT extension (long file names).


Installation
------------

To install fs.fat just run from the root of the project:

.. code-block:: bash

    $ python setup.py install


Usage
-----
Opener
''''''

Use fs.open_fs to open a filesystem with a FAT `FS URL <https://pyfilesystem2.readthedocs.io/en/latest/openers.html>`_:

.. code-block:: python

    import fs
    my_fs = fs.open_fs("fat:///dev/sda1")

The following URL parameter is supported: encoding (defaults to ibm437).


Testing
-------

Tests are located at the `tests` directory. In order to test your new
contribution to fs.fat just run

.. code-block:: bash

    $ python setup.py test

from your shell.


Contribute
----------

Feel free to contribute improvements to this package via mail or pull request.

The preferred method of development is a test driven approach and following
the nvie git flow branching model. Please be so kind to bear these things in
mind when handing in improvements. Thank you very much.
