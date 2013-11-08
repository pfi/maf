import unittest
import json
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
        """Add executing tests.

        :param tests_list: The adding tests that specified in the following way:

        - file name (ends with .py): find test class in that files
        - directory name: find all test classes in files in the directory
        - class name: add tests defined in the class

        """
        
        if not isinstance(tests_list, dict): tests_list = [tests_list]
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
            (dirname, filename) = (test_path[0:last_slash], test_path[last_slash+1:])
        else:
            (dirname, filename) = (".", test_path)
        self.tests += unittest.defaultTestLoader.discover(dirname, pattern=filename)
        
    def add_test_in_dir(self, dir_path):
        self.tests += unittest.defaultTestLoader.discover(dir_path)
        
    def add_test_in_class(self, cls):
        self.tests.append(unittest.TestLoader().loadTestsFromTestCase(cls))

        
class TestTask(object):
    """A task object making easy to write unittest for rules.

    This class mimics the behavior of task object by having dummy Node objects internally.
    These node objects are :py:func:`maflib.core.ExperimentNode`.
    
    Example usages of this task can be found on test_rules.py.
    
    """
    
    class ExperimentNodeList(object):
        def __init__(self):
            self.list = []
            
        def __getitem__(self, index):
            if index <= len(self.list):
                for i in range(len(self.list) - index + 1):
                    self.list.append(maflib.core.ExperimentNode())
            return self.list[index]
        
    def __init__(self):
        self.inputs = TestTask.ExperimentNodeList()
        self.outputs = TestTask.ExperimentNodeList()

        self.env = ConfigSet()
        """The ConfigSet is a waf module which is used as a dictionary to store any attributes.
        
        The values can be accessed both by attributes or by keys;

        .. code-block:: py

            task = TestTask()
            task.env.FOO = 'test'
            task.env['FOO'] # => 'test'
        
        """

        self.parameter = {}
        
    def set_input(self, index, s):
        self.inputs[index].write(s)

    def set_input_by_json(self, index, obj):
        self.inputs[index].write(json.dumps(obj))
        
    def json_output(self, index): return json.loads(self.outputs[index].read())
