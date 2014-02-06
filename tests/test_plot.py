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

from maflib.plot import *
import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

class TestPlotData(unittest.TestCase):
    inputs = [
        { 'x': 1, 'y': 2, 'z': 50, 'k': 'p' },
        { 'x': 5, 'y': 3, 'z': 25, 'k': 'q' },
        { 'x': 3, 'y': 5, 'z': 10, 'k': 'q' },
        { 'x': 7, 'y': 4, 'z': 85, 'k': 'p' }
    ]

    def test_empty_inputs(self):
        pd = PlotData([])
        data = pd.get_data_1d('x')
        self.assertListEqual([], data)

    def test_get_data_1d(self):
        pd = PlotData(self.inputs)
        data = pd.get_data_1d('x')
        self.assertListEqual([1, 3, 5, 7], data)

    def test_get_data_1d_unsorted(self):
        pd = PlotData(self.inputs)
        data = pd.get_data_1d('x', sort=False)
        self.assertListEqual([1, 5, 3, 7], data)

    def test_get_data_1d_with_key(self):
        pd = PlotData(self.inputs)
        data = pd.get_data_1d('x', key='k')
        self.assertDictEqual({ 'p': [1, 7], 'q': [3, 5] }, data)

    def test_get_data_1d_unsorted_with_key(self):
        pd = PlotData(self.inputs)
        data = pd.get_data_1d('x', key='k', sort=False)
        self.assertDictEqual({ 'p': [1, 7], 'q': [5, 3] }, data)

    def test_get_data_2d(self):
        pd = PlotData(self.inputs)
        data = pd.get_data_2d('x', 'y')
        self.assertEqual(2, len(data))
        self.assertListEqual([1, 3, 5, 7], data[0])
        self.assertListEqual([2, 5, 3, 4], data[1])

    def test_get_data_2d_unsorted(self):
        pd = PlotData(self.inputs)
        data = pd.get_data_2d('x', 'y', sort=False)
        self.assertEqual(2, len(data))
        self.assertListEqual([1, 5, 3, 7], data[0])
        self.assertListEqual([2, 3, 5, 4], data[1])

    def test_get_data_2d_with_key(self):
        pd = PlotData(self.inputs)
        data = pd.get_data_2d('x', 'y', key='k')
        self.assertDictEqual(
            { 'p': ([1, 7], [2, 4]), 'q': ([3, 5], [5, 3]) }, data)

    def test_get_data_2d_unsorted_with_key(self):
        pd = PlotData(self.inputs)
        data = pd.get_data_2d('x', 'y', key='k', sort=False)
        self.assertDictEqual(
            { 'p': ([1, 7], [2, 4]), 'q': ([5, 3], [3, 5]) }, data)

    def test_get_data_3d(self):
        pd = PlotData(self.inputs)
        data = pd.get_data_3d('x', 'y', 'z')
        self.assertEqual(3, len(data))
        self.assertListEqual([1, 3, 5, 7], data[0])
        self.assertListEqual([2, 5, 3, 4], data[1])
        self.assertListEqual([50, 10, 25, 85], data[2])

    def test_get_data_3d_unsorted(self):
        pd = PlotData(self.inputs)
        data = pd.get_data_3d('x', 'y', 'z', sort=False)
        self.assertEqual(3, len(data))
        self.assertListEqual([1, 5, 3, 7], data[0])
        self.assertListEqual([2, 3, 5, 4], data[1])
        self.assertListEqual([50, 25, 10, 85], data[2])

    def test_get_data_3d_with_key(self):
        pd = PlotData(self.inputs)
        data = pd.get_data_3d('x', 'y', 'z', key='k')
        self.assertDictEqual({
            'p': ([1, 7], [2, 4], [50, 85]),
            'q': ([3, 5], [5, 3], [10, 25])
        }, data)

    def test_Get_data_3d_unsorted_with_key(self):
        pd = PlotData(self.inputs)
        data = pd.get_data_3d('x', 'y', 'z', key='k', sort=False)
        self.assertDictEqual({
            'p': ([1, 7], [2, 4], [50, 85]),
            'q': ([5, 3], [3, 5], [25, 10])
        }, data)
