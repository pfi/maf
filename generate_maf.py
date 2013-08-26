#!/usr/bin/env python
# coding: utf-8

import os
import tarfile

TEMPLATE_FILE_NAME = 'maf_template.py'
TARGET_FILE_NAME = 'maf.py'
ARCHIVE_FILE_NAME = 'maflib.tar.bz2'
MAFLIB_PATH = 'maflib'

NEW_LINE = '#XXX'.encode()
CARRIAGE_RETURN = '#YYY'.encode()

ARCHIVE_BEGIN = '#==>\n#'.encode()
ARCHIVE_END = '#<==\n#'.encode()

if __name__ == '__main__':
    with tarfile.open(ARCHIVE_FILE_NAME, 'w:bz2') as archive:
        archive.add(MAFLIB_PATH, exclude=lambda fn: fn.endswith('.pyc'))

    with open(TEMPLATE_FILE_NAME) as f:
        code = f.read()

    with open(ARCHIVE_FILE_NAME, 'rb') as f:
        archive = f.read()

    code += '#==>\n#'.encode()
    code += archive.replace('\n'.encode(), NEW_LINE).replace('\r'.encode(), CARRIAGE_RETURN)
    code += '\n#<==\n'.encode()

    with open(TARGET_FILE_NAME, 'wb') as f:
        f.write(code)

    os.unlink(ARCHIVE_FILE_NAME)
