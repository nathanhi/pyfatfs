# -*- coding: utf-8 -*-

"""8DOT3 file name helper class & functions."""

import errno
import os
import string

from pyfatfs import FAT_OEM_ENCODING
from pyfatfs._exceptions import PyFATException, NotAFatEntryException


def _init_check(func):
    def _wrapper(*args, **kwargs):
        initialised = args[0].initialised

        if initialised is True:
            return func(*args, **kwargs)
        else:
            raise PyFATException("Class has not yet been fully initialised, "
                                 "please instantiate first.")

    return _wrapper


class EightDotThree:
    """8DOT3 filename representation."""

    #: Length of the byte representation in a directory entry header
    SFN_LENGTH = 11

    #: Valid characters for 8.3 file names
    VALID_CHARACTERS = f"{string.ascii_letters.upper()}{string.digits}" \
                       "!#$%&'()-@^_`{}~"

    def __init__(self, encoding: str = FAT_OEM_ENCODING):
        """Offer 8DOT3 filename operation.

        :param encoding: Codepage for the 8.3 filename.
                         Defaults to `FAT_OEM_ENCODING` as per FAT spec.
        """
        self.name: bytes = None
        self.encoding = encoding
        self.initialised = False

    @_init_check
    def byte_repr(self):
        """Byte representation of the 8DOT3 name dir entry headers."""
        return self.name

    @_init_check
    def get_unpadded_filename(self) -> str:
        """Retrieve the human readable filename."""
        base = self.name[:8].decode(self.encoding).rstrip()
        ext = self.name[8:11].decode(self.encoding).rstrip()
        sep = "." if len(ext) > 0 else ""

        return sep.join([base, ext])

    @staticmethod
    def __raise_8dot3_nonconformant(name: str):
        raise PyFATException(f"Given directory name "
                             f"{name} is not conform "
                             f"to 8.3 file naming convention.",
                             errno=errno.EINVAL)

    def __set_name(self, name: bytes):
        """Set self.name and verify for correctness."""
        name_str = name.decode(self.encoding)
        if len(name_str) != 11:
            self.__raise_8dot3_nonconformant(name_str)

        self.name = name
        self.initialised = True

    def set_byte_name(self, name: bytes):
        """Set the name as byte input from a directory entry header.

        :param name: `bytes`: Padded (must be 11 bytes) 8dot3 name
        """
        if not isinstance(name, bytes):
            raise TypeError(f"Given parameter must be of type bytes,"
                            f"but got {type(name)} instead.")

        if len(name) != 11:
            raise ValueError("Invalid byte name supplied, must be exactly "
                             "11 bytes long (8+3).")

        if name[0] == 0x0 or name[0] == 0xE5:
            # Empty directory entry
            raise NotAFatEntryException("Given dir entry is invalid and has "
                                        "no valid name.", free_type=name[0])

        if name[0] == 0x05:
            # Translate 0x05 to 0xE5
            name = name.replace(bytes(0x05), bytes(0xE5), 1)

        self.__set_name(name)

    def set_str_name(self, name: str):
        """Set the name as string from user input (i.e. folder creation)."""
        if not isinstance(name, str):
            raise TypeError(f"Given parameter must be of type str,"
                            f"but got {type(name)} instead.")

        if not self.is_8dot3_conform(name):
            self.__raise_8dot3_nonconformant(name)

        name = self._pad_8dot3_name(name)
        self.__set_name(name.encode(self.encoding))

    @_init_check
    def checksum(self) -> int:
        """Calculate checksum of byte string.

        :returns: Checksum as int
        """
        chksum = 0
        for c in self.name:
            chksum = ((chksum >> 1) | (chksum & 1) << 7) + c
            chksum &= 0xFF
        return chksum

    @staticmethod
    def __check_characters(name: str) -> bool:
        """Test if given string contains invalid chars for 8.3 names.

        :param name: `str`: Filename to parse
        :raises: `ValueError` if the given string contains invalid
                 8.3 filename characters.
        """
        vc = EightDotThree.VALID_CHARACTERS
        n = ''.join(filter(lambda x: x in vc, name))
        if n != name:
            raise ValueError(f"Invalid characters in string '{name}', "
                             f"cannot be used as part of an 8.3 "
                             f"conform file name.")

    @staticmethod
    def is_8dot3_conform(entry_name: str):
        """Indicate conformance of given entries name to 8.3 standard.

        :param entry_name: Name of entry to check
        :returns: bool indicating conformance of name to 8.3 standard
        """
        if entry_name != entry_name.upper():
            # Case sensitivity check
            return False

        root, ext = os.path.splitext(entry_name)
        ext = ext[1:]
        if len(root) + len(ext) > 11:
            return False
        elif len(root) > 8 or len(ext) > 3:
            return False

        # Check for valid characters in both filename segments
        for i in [root, ext]:
            try:
                EightDotThree.__check_characters(i)
            except ValueError:
                return False

        return True

    @staticmethod
    def _pad_8dot3_name(name: str):
        """Pad 8DOT3 name to 11 bytes for header operations.

        This is required to pass the correct value to the `FATDirectoryEntry`
        constructor as a DIR_Name.
        """
        root, ext = os.path.splitext(name)
        ext = ext[1:]
        name = root.strip().ljust(8) + ext.strip().ljust(3)
        return name

    @staticmethod
    def make_8dot3_name(dir_name: str,
                        parent_dir_entry) -> str:
        """Generate filename based on 8.3 rules out of a long file name.

        In 8.3 notation we try to use the first 6 characters and
        fill the rest with a tilde, followed by a number (starting
        at 1). If that entry is already given, we increment this
        number and try again until all possibilities are exhausted
        (i.e. A~999999.TXT).

        :param dir_name: Long name of directory entry.
        :param parent_dir_entry: `FATDirectoryEntry`: Dir entry of parent dir.
        :returns: `str`: 8DOT3 compliant filename.
        :raises: PyFATException: If parent dir is not a directory
                                 or all name generation possibilities
                                 are exhausted
        """
        dirs, files, _ = parent_dir_entry.get_entries()
        dir_entries = [e.get_short_name() for e in dirs + files]

        extsep = "."

        def map_chars(char: chr) -> chr:
            """Map 8DOT3 valid characters.

            :param char: `str`: input character
            :returns: `str`: mapped output character
            """
            char = char.upper()
            if char == ' ':
                return ''
            if char not in EightDotThree.VALID_CHARACTERS:
                return '_'
            return char

        try:
            # Shorten to 8 chars; strip invalid characters
            basename = os.path.splitext(dir_name)[0][0:8].strip()
            basename = ''.join(map(map_chars, basename))
        except IndexError:
            basename = ""

        try:
            # Shorten to 3 chars; strip invalid characters
            extname = os.path.splitext(dir_name)[1][1:4].strip()
            extname = ''.join(map(map_chars, extname))
        except IndexError:
            extname = ""

        if len(extname) == 0:
            extsep = ""

        # Loop until suiting name is found
        i = 0
        while len(str(i)) + 1 <= 7:
            if i > 0:
                maxlen = 8 - (1 + len(str(i)))
                basename = f"{basename[0:maxlen]}~{i}"

            short_name = f"{basename}{extsep}{extname}"

            if short_name not in dir_entries:
                return short_name
            i += 1

        raise PyFATException("Cannot generate 8dot3 filename, "
                             "unable to find suiting short file name.",
                             errno=errno.EEXIST)
