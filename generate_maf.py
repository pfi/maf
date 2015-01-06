#!/usr/bin/env python
# coding: utf-8
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

import os
import tarfile
import re
import subprocess
import tempfile
import shutil

VERSION = '0.2' # This value should be updated when releasing new version (?)

TEMPLATE_FILE_NAME = 'maf_template.py'
TARGET_FILE_NAME = 'maf.py'
ARCHIVE_FILE_NAME = 'maflib.tar.bz2'
MAFLIB_PATH = 'maflib'

NEW_LINE = '#XXX'.encode()
CARRIAGE_RETURN = '#YYY'.encode()

ARCHIVE_BEGIN = '#==>\n#'.encode()
ARCHIVE_END = '#<==\n#'.encode()

def compute_maf_revision():
    p = subprocess.Popen("git rev-parse HEAD",
                         shell = 'True',
                         stdout = subprocess.PIPE,
                         stderr = subprocess.PIPE)
    out, err = p.communicate()
    out = out.strip()
    err = err.strip()

    if err:
        print(err)
        return 'xxx'
    return out

def fill_version(code, version, revision):
    patterns = []
    patterns.append(('^MAFVERSION = (.*)', 'MAFVERSION = "%s"' % version))
    patterns.append(('^MAFREVISION = (.*)', 'MAFREVISION = "%s"' % revision))

    for (orig, rep) in patterns:
        re_pat = re.compile(orig, re.M)
        code = re_pat.sub(rep, code)

    return code

def fill_version_in_file(name, version, revision):
    with open(name) as f:
        txt = f.read()
    txt = fill_version(txt, version, revision)
    
    with open(name, 'w') as f:
        f.write(txt)

def add_versioned_files(archive, version, revision):
    temp_dir = tempfile.mkdtemp()
    temp_maflib = os.path.join(temp_dir, 'maflib')
    shutil.copytree(MAFLIB_PATH, temp_maflib)

    fill_version_in_file(os.path.join(temp_maflib, 'core.py'), version, revision)

    # exclude is obsolete
    archive.add(temp_maflib, arcname=MAFLIB_PATH,
                filter=lambda info: None if info.name.endswith('.pyc') else info)

    return archive
    
if __name__ == '__main__':
    
    REVISION = compute_maf_revision()

    try:
        archive = tarfile.open(ARCHIVE_FILE_NAME, 'w:bz2')
        archive = add_versioned_files(archive, VERSION, REVISION)
        
    except tarfile.TarError:
        raise Exception('can not use tar.bz2 file')
    finally:
        archive.close()
   
    with open(TEMPLATE_FILE_NAME) as f:
        code = f.read()
        
    code = fill_version(code, VERSION, REVISION)

    with open(ARCHIVE_FILE_NAME, 'rb') as f:
        archive = f.read()

    code += '#==>\n#'.encode()
    code += archive.replace('\n'.encode(), NEW_LINE).replace('\r'.encode(), CARRIAGE_RETURN)
    code += '\n#<==\n'.encode()

    with open(TARGET_FILE_NAME, 'wb') as f:
        f.write(code)

    os.unlink(ARCHIVE_FILE_NAME)
