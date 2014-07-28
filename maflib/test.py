import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest
import json
import waflib
import waflib.Context
from waflib.ConfigSet import ConfigSet
import maflib.core

class ExpTestContext(waflib.Context.Context):
    """A context class for executing unittests of maf."""

    cmd = 'exptest'
    fun = 'exptest'

    def __init__(self, **kw):
        super(ExpTestContext, self).__init__(**kw)

        self.tests = []

    def execute(self):
        """
        See :py:func:`waflib.Context.Context.execute`
        """
        super(ExpTestContext, self).execute()

        self.tests = self.unique_(self.tests)
        suite = unittest.TestSuite(self.tests)

        unittest.TextTestRunner(verbosity=2).run(suite)

    def unique_(self, l):
        from collections import OrderedDict
        # takes unique from a list of un-hashable values
        test_k2v = OrderedDict(zip([str(t) for t in self.tests], self.tests))
        return test_k2v.values()

    def add(self, tests_list):
        """Adds executing tests.

        :param tests_list: Tests to add, specified in the following way:

        - file name (ends with .py): find all test classes in that file
        - directory name: find all test classes in files matching 'test*.py' in the directory
        - class name: add tests defined in the class

        """

        if not isinstance(tests_list, list): tests_list = waflib.Utils.to_list(tests_list)
        for test in tests_list:
            if isinstance(test, str):
                if test.endswith(".py"):
                    self.add_test_in_path(test)
                else:
                    self.add_test_in_dir(test)
            if isinstance(test, type):
                self.add_test_in_class(test)

    def add_test_in_path(self, test_path):
        last_slash = test_path.rfind("/")
        if last_slash != -1:
            (dir_path, filename) = (test_path[0:last_slash], test_path[last_slash+1:])
        else:
            (dir_path, filename) = (".", test_path)
        self.tests += unittest.defaultTestLoader.discover(dir_path, pattern=filename, top_level_dir=dir_path)

    def add_test_in_dir(self, dir_path):
        self.tests += unittest.defaultTestLoader.discover(dir_path, top_level_dir=dir_path)

    def add_test_in_class(self, cls):
        self.tests.append(unittest.TestLoader().loadTestsFromTestCase(cls))


class TestTask(object):
    """A task object making it easy to write unittest for rules.

    This class mimics the behavior of task object by having dummy Node objects
    internally. These node objects are :py:func:`maflib.core.ExperimentNode`.

    Example usages of this task can be found on test_rules.py.

    `inputs` and `outputs` are instances of `ExperimentNodeList`.
    This class makes easy for accessing input/output node objects by
    automatically adding new element if necessary.
    NOTE: You should not add elements to this list manually, e.g., with
    `task.outputs.append(...)`. Please use instead `setsize(size)` or
    index accessing like `task.outputs[3]` automatically appends elements up to
    the index 2.

    """

    class ExperimentNodeList(list):
        def setsize(self, size):
            if len(self) <= size:
                for i in range(size - len(self)):
                    self.append(maflib.core.ExperimentNode())

        def __getitem__(self, index):
            if index <= len(self):
                self.setsize(index + 1)
            return super(TestTask.ExperimentNodeList, self).__getitem__(index)

    def __init__(self):
        self.inputs = TestTask.ExperimentNodeList()
        self.outputs = TestTask.ExperimentNodeList()

        self.env = ConfigSet()
        """A ConfigSet to store any attributes.

        ConfigSet is a class defined by waflib which is used as a dictionary to
        store any attributes. Its values can be accessed both by attributes or
        by keys;

        .. code-block:: py

            task = TestTask()
            task.env.FOO = 'test'
            task.env['FOO'] # => 'test'

        """

        self.parameter = {}
        self.source_parameters = []

    def set_input(self, index, s):
        self.inputs[index].write(s)

    def set_input_by_json(self, index, obj):
        self.inputs[index].write(json.dumps(obj))

    def json_output(self, index): return json.loads(self.outputs[index].read())
