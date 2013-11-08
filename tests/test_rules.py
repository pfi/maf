from maflib import rules
#import maflib.rules
import waflib.Node
import unittest
import json
from maflib.test import TestTask

class TestAggregationTask(unittest.TestCase):
    def test_max(self):
        task = TestTask()
        task.env.source_parameter = [({"param1":0}), {"param1":1}]

        task.set_input_by_json(0, {"key1":10, "key2":20})
        task.set_input_by_json(1, {"key1": 5, "key2":30})
        
        rule = rules.max("key1")
        rule.fun(task)

        result = task.json_output(0)
        self.assertEqual(result, {"param1": 0, "key1": 10, "key2": 20})

class TestMulticlassEvaluation(unittest.TestCase):
    def label(self, (p, c)): return {"p":p, "c":c}
    def test_multilabel_evaluation(self):
        task = TestTask()
        task.set_input_by_json(0, map(self.label, [(1,1),(1,2),(2,2),(2,2)]))
        
        rules.calculate_stats_multiclass_classification(task)
        result = task.json_output(0)
        
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
