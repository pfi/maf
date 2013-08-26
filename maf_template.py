#!/usr/bin/env python
# coding: ISO8859-1

"""
maf - a waf extension for automation of parameterized computational experiments
"""

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

        with tarfile.open(TEMPORARY_FILE_NAME) as t:
            t.extractall()

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
