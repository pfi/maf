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

from maflib.util import *
from maflib.core import Parameter
import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

class TestProduct(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual([{}], product({}))

    def test_single_key(self):
        params = product({ 'key': [0, 1, 2] })
        expect = [{ 'key': 0 }, { 'key': 1 }, { 'key': 2 }]
        self.assertListEqual(expect, params)

    def test_two_keys(self):
        params = product({ 'a': [0, 1, 2], 'b': ['x', 'y'] })
        expect = [{ 'a': 0, 'b': 'x' },
                  { 'a': 0, 'b': 'y' },
                  { 'a': 1, 'b': 'x' },
                  { 'a': 1, 'b': 'y' },
                  { 'a': 2, 'b': 'x' },
                  { 'a': 2, 'b': 'y' }]
        self.assertSetEqual(set(Parameter(e) for e in expect),
                            set(Parameter(p) for p in params))

    def test_empty_value_for_some_key(self):
        params = product({ 'a': [0, 1], 'b': ['x', 'y'], 'c': [] })
        self.assertEqual([], params)


class TestSample(unittest.TestCase):
    def test_zero_sample(self):
        params = sample(0, { 'key': [0, 1] })
        self.assertEqual([], params)

    def test_empty_distribution(self):
        params = sample(1, {})
        self.assertListEqual([{}], params)

    def test_sample_from_interval(self):
        params = sample(100, { 'key': (-2, 3) })
        for param in params:
            self.assertGreater(param['key'], -2)
            self.assertLess(param['key'], 3)

    def test_sample_from_list(self):
        values = set(('a', 'b', 'c', 'x', 'y', 'z'))
        params = sample(100, { 'key': list(values) })
        for param in params:
            self.assertIn(param['key'], values)

    def test_sample_from_function(self):
        i = [0]
        def gen():
            i[0] += 1
            return i[0] % 3

        expects = [1, 2, 0, 1, 2, 0]
        params = sample(6, { 'key': gen })
        for param, expect in zip(params, expects):
            self.assertEqual(expect, param['key'])
