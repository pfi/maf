#!/usr/bin/env python
# coding: utf-8

import unittest

try:
    import waflib
except ImportError:
    import glob
    import sys
    dirs = glob.glob('.waf-1.*')
    if not dirs:
        import subprocess
        with open('/dev/null') as null:
            subprocess.call(['python', 'waf'], stdout=null, stderr=null)
        dirs = glob.glob('.waf-1.*')
    sys.path.append(dirs[0])

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.discover('tests')
    runner = unittest.TextTestRunner()
    runner.run(suite)
