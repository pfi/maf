#!/usr/bin/env python

"""
Prepares for running samples.
It just generates maf.py and copies maf.py and waf to each sample directory.
Please run this script before trying these samples.
"""

import glob
import os
import shutil
import subprocess

if __name__ == '__main__':
    os.chdir('..')
    subprocess.check_call('./generate_maf.py')
    os.chdir('samples')

    for d in glob.glob('*/'):
        for dotwaf in glob.glob(os.path.join(d, ".waf-*")):
            shutil.rmtree(dotwaf)
        for f in '../maf.py', '../waf':
            shutil.copy(f, d)
