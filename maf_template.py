#!/usr/bin/env python
# coding: ISO8859-1
#
# Copyright (c) 2013, Preferred Infrastructure, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
maf - a waf extension for automation of parameterized computational experiments
"""

# NOTE: coding ISO8859-1 is necessary for attaching maflib at the end of this
# file.

import os
import os.path
import shutil
import subprocess
import sys
import tarfile
import waflib.Context
import waflib.Logs

TEMPORARY_FILE_NAME = 'maflib.tar.bz2'
NEW_LINE = '#XXX'.encode()
CARRIAGE_RETURN = '#YYY'.encode()
ARCHIVE_BEGIN = '#==>\n'.encode()
ARCHIVE_END = '#<==\n'.encode()

class _Cleaner:
    def __init__(self, directory):
        self._cwd = os.getcwd()
        self._directory = directory

    def __enter__(self):
        self.clean()

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self._cwd)
        if exc_type:
            self.clean()
        return False

    def clean(self):
        try:
            path = os.path.join(self._directory, 'maflib')
            shutil.rmtree(path)
        except OSError:
            pass

def _read_archive(filename):
    if filename.endswith('.pyc'):
        filename = filename[:-1]

    with open(filename, 'rb') as f:
        while True:
            line = f.readline()
            if not line:
                raise Exception('archive not found')
            if line == ARCHIVE_BEGIN:
                content = f.readline()
                if not content or f.readline() != ARCHIVE_END:
                    raise Exception('corrupt archive')
                break

    return content[1:-1].replace(NEW_LINE, '\n'.encode()).replace(
        CARRIAGE_RETURN, '\r'.encode())

def unpack_maflib(directory):
    with _Cleaner(directory) as c:
        content = _read_archive(__file__)

        os.makedirs(os.path.join(directory, 'maflib'))
        os.chdir(directory)

        with open(TEMPORARY_FILE_NAME, 'wb') as f:
            f.write(content)

        try:
            t = tarfile.open(TEMPORARY_FILE_NAME)
            t.extractall()
        except tarfile.TarError:
            raise Exception('can not open maflib tar file')
        finally:
            t.close()

        os.remove(TEMPORARY_FILE_NAME)

        maflib_path = os.path.abspath(os.getcwd())
        # sys.path[:0] = [maflib_path]
        return maflib_path

def test_maflib(directory):
    try:
        os.stat(os.path.join(directory, 'maflib'))
        return os.path.abspath(directory)
    except OSError:
        return None

def find_maflib():
    path = waflib.Context.waf_dir
    if not test_maflib(path):
        unpack_maflib(path)
    return path

find_maflib()
from maflib import *

def configure(conf):
    try:
        conf.env.MAFLIB_PATH = find_maflib()
        conf.msg('Unpacking maflib', 'yes')
        conf.load('maflib.core')
    except:
        conf.msg('Unpacking maflib', 'no')
        waflib.Logs.error(sys.exc_info()[1])

def options(opt):
    try:
        find_maflib()
        opt.load('maflib.core')
    except:
        opt.msg('Unpacking maflib', 'no')
        waflib.Logs.error(sys.exc_info()[1])
