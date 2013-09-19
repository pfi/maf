from maflib.rules import *
import unittest
import json

class MulticlassEvaluationTask(object):
    """This is dummy class for the use of a test below.
    When task object is separated from a rule, this class would be unnecessary.
    
    """
    class DummyInput(object):
        def label(self, (p, c)): return {"p":p, "c":c}
        def read(self):
            return json.dumps(map(self.label, [(1,1),(1,2),(2,2),(2,2)]))
    class DummyOutput(object):
        def write(self, s): self.body = s
        def read(self): return self.body
    def __init__(self):
        self.inputs = [MulticlassEvaluationTask.DummyInput()]
        self.outputs = [MulticlassEvaluationTask.DummyOutput()]

class TestMulticlassEvaluation(unittest.TestCase):
    def test_multilabel_evaluation(self):
        result = self._get_result_json()
        
        self.assertEqual(result["accuracy"], 3./4)
        self.assertEqual(result["average_accuracy"], 3./4)
        self.assertEqual(result["error_rate"], 1./4)
        self.assertEqual(result["1-precision"], 1./2)
        self.assertEqual(result["2-precision"], 1)
        self.assertEqual(result["1-recall"], 1)
        self.assertEqual(result["2-recall"], 2./3)
        self.assertEqual(result["1-F1"], 2./3)
        self.assertEqual(result["precision-micro"], 3./4)
        self.assertEqual(result["recall-micro"], 3./4)
        self.assertEqual(result["precision-macro"], 3./4)

    def _get_result_json(self):
        task = MulticlassEvaluationTask()
        calculate_stats_multilabel_classification(task)
        return json.loads(task.outputs[0].read())
        
