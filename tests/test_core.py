import maflib.core
import unittest

class TestParameter(unittest.TestCase):
    def test_empty_parameter_does_not_conflict(self):
        p = maflib.core.Parameter()
        q = maflib.core.Parameter()
        self.assertFalse(p.conflict_with(q))

    def test_empty_parameter_to_str(self):
        p = maflib.core.Parameter()
        p_str = p.to_str_valued_dict()
        self.assertDictEqual({}, p_str)

    def test_conflicted_parameters(self):
        p = maflib.core.Parameter(a=1, b=2, c=3)
        q = maflib.core.Parameter(a=2, b=2, d=4)
        self.assertTrue(p.conflict_with(q))

    def test_not_conflicted_parameters(self):
        p = maflib.core.Parameter(a=1, b=2, c=3)
        q = maflib.core.Parameter(a=1, b=2, d=4)
        self.assertFalse(p.conflict_with(q))

    def test_dict_with_parameter_keys(self):
        d = {}
        d[maflib.core.Parameter(a=1)] = 1
        d[maflib.core.Parameter(a=1, b=2)] = 2
        d[maflib.core.Parameter(a=2)] = 3

        self.assertEqual(1, d[maflib.core.Parameter(a=1)])
        self.assertEqual(2, d[maflib.core.Parameter(a=1, b=2)])
        self.assertEqual(3, d[maflib.core.Parameter(a=2)])

    def test_dict_with_parameter_keys_modified(self):
        d = {}
        d[maflib.core.Parameter(a=1, b=2)] = 1

        p = maflib.core.Parameter()
        p['a'] = 1
        p['c'] = 3
        p['b'] = 2
        del p['c']

        self.assertEqual(1, d[p])

    def test_dict_with_parameter_keys_not_exist(self):
        d = {}
        d[maflib.core.Parameter(a=1)] = 1
        d[maflib.core.Parameter(a=1, b=2)] = 2

        self.assertFalse(maflib.core.Parameter(a=2) in d)
        self.assertFalse(maflib.core.Parameter(a=1, b=2, c=3) in d)
