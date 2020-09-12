Test data assets
================

Since pyfat is not yet able to format a filesystem on-the-fly but
we need one for the unit tests, these files consist of empty filesystem
images that have been pre-created.

Image file recreation
^^^^^^^^^^^^^^^^^^^^^

In order to re-create these filesystem images, the following commands are
needed:

.. code-block:: shell

    # FAT12
    dd if=/dev/zero of=pyfat12.img bs=1M count=2
    /sbin/mkfs.fat -F12 -i DEADBEEF -n FAT12TEST pyfat12.img
    gzip -9 pyfat12.img

    # FAT16
    dd if=/dev/zero of=pyfat16.img bs=1M count=16
    /sbin/mkfs.fat -F16 -i DEADBEEF -n FAT16TEST pyfat16.img
    gzip -9 pyfat16.img

    # FAT32
    dd if=/dev/zero of=pyfat32.img bs=1M count=64
    /sbin/mkfs.fat -F32 -i DEADBEEF -n FAT16TEST pyfat32.img
    gzip -9 pyfat32.img