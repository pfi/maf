import unittest
from maflib.test import TestTask
import vowpal_util

class TestVowpalUtil(unittest.TestCase):
    libsvm_example = """1 197:0.18 321:0.18
2 7:0.21 1039:0.21 1628:0.21"""

    vowpal_example = """1 | 197:0.18 321:0.18
2 | 7:0.21 1039:0.21 1628:0.21"""
    
    def test_convert_format(self):
        task = TestTask()
        task.set_input(0, self.libsvm_example)

        vowpal_util.convert_libsvm_format_to_vowpal(task)

        self.assertEqual(task.outputs[0].read(), self.vowpal_example)

    def test_num_classes(self):
        task = TestTask()
        task.set_input(0, self.vowpal_example)

        vowpal_util.num_classes(task)

        self.assertEqual(int(task.outputs[0].read()), 2)
