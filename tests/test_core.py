from maflib.core import *
import unittest

class TestParameter(unittest.TestCase):
    def test_empty_parameter_does_not_conflict(self):
        p = Parameter()
        q = Parameter()
        self.assertFalse(p.conflict_with(q))

    def test_empty_parameter_to_str(self):
        p = Parameter()
        p_str = p.to_str_valued_dict()
        self.assertDictEqual({}, p_str)

    def test_conflicted_parameters(self):
        p = Parameter(a=1, b=2, c=3)
        q = Parameter(a=2, b=2, d=4)
        self.assertTrue(p.conflict_with(q))

    def test_not_conflicted_parameters(self):
        p = Parameter(a=1, b=2, c=3)
        q = Parameter(a=1, b=2, d=4)
        self.assertFalse(p.conflict_with(q))

    def test_dict_with_parameter_keys(self):
        d = {}
        d[Parameter(a=1)] = 1
        d[Parameter(a=1, b=2)] = 2
        d[Parameter(a=2)] = 3

        self.assertEqual(1, d[Parameter(a=1)])
        self.assertEqual(2, d[Parameter(a=1, b=2)])
        self.assertEqual(3, d[Parameter(a=2)])

    def test_dict_with_parameter_keys_modified(self):
        d = {}
        d[Parameter(a=1, b=2)] = 1

        p = Parameter()
        p['a'] = 1
        p['c'] = 3
        p['b'] = 2
        del p['c']

        self.assertEqual(1, d[p])

    def test_dict_with_parameter_keys_not_exist(self):
        d = {}
        d[Parameter(a=1)] = 1
        d[Parameter(a=1, b=2)] = 2

        self.assertFalse(Parameter(a=2) in d)
        self.assertFalse(Parameter(a=1, b=2, c=3) in d)
