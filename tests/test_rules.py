from maflib import rules
#import maflib.rules
import waflib.Node
import collections
import unittest
import json
from maflib.test import TestTask
import tempfile

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

    def test_min(self):
        task = TestTask()
        task.env.source_parameter = [{"param1":0}, {"param1":1}]

        task.set_input_by_json(0, {"key1":10, "key2":20})
        task.set_input_by_json(1, {"key1": 5, "key2":30})

        rule = rules.min("key1")
        rule.fun(task)

        result = task.json_output(0)
        self.assertEqual(result, {"param1": 1, "key1": 5, "key2": 30})


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

    def _get_result_json(self):
        task = MulticlassEvaluationTask()
        calculate_stats_multiclass_classification(task)
        return json.loads(task.outputs[0].read())

# TODO(noji): change the test style to use test module after merging
class SegmentLibsvmTask(object):
    class Node(object):
        def __init__(self, f):
            self.abspath_ = f.name
        def abspath(self): return self.abspath_
        
    def _create_dummy_input(self, data):
        self.f = tempfile.NamedTemporaryFile()
        for e in data: self.f.write(' '.join([str(x) for x in e]) + '\n')
        self.f.seek(0)
        return SegmentLibsvmTask.Node(self.f)

    def __init__(self, data, num_segments):
        self.inputs = [self._create_dummy_input(data)]
        self.ofs = [tempfile.NamedTemporaryFile() for i in range(num_segments)]
        self.outputs = [SegmentLibsvmTask.Node(of) for of in self.ofs]

class TestSegmentLibsvm(unittest.TestCase):
    weights = [0.8, 0.1, 0.1]
    labels = [0, 1]
    def _example(self, label): return [label] + [1,1,2]
    
    def _count_num_labels(self, o):
        segmented = [e.split(' ') for e in open(o.abspath())]
        counts = collections.defaultdict(int)
        for l in [int(e[0]) for e in segmented]: counts[l] += 1
        return counts

    def _process_task(self, data):
        task = SegmentLibsvmTask(data, len(self.weights))
        rule = rules.segment_without_label_bias(self.weights)
        rule.fun(task)
        return task
    
    def test_round_number(self):
        # 10 label-0 examples and 10 label-1 examples
        data = [self._example(l) for l in self.labels for i in range(10)]
        task = self._process_task(data)

        zero_label2count = self._count_num_labels(task.outputs[0])
        self.assertEqual(zero_label2count[0], 8)
        self.assertEqual(zero_label2count[1], 8)
        one_label2count = self._count_num_labels(task.outputs[1])
        self.assertEqual(one_label2count[0], 1)
        self.assertEqual(one_label2count[1], 1)
        two_label2count = self._count_num_labels(task.outputs[2])
        self.assertEqual(two_label2count[0], 1)
        self.assertEqual(two_label2count[1], 1)

    def test_nonround_number(self):
        # 11 label-0 examples and 10 label-1 examples
        data = [self._example(0) for i in range(11)] + [self._example(1) for i in range(10)]
        task = self._process_task(data)

        zero_label2count = self._count_num_labels(task.outputs[0])
        self.assertEqual(zero_label2count[0], 8)
        self.assertEqual(zero_label2count[1], 8)
        one_label2count = self._count_num_labels(task.outputs[1])
        self.assertEqual(one_label2count[0], 1)
        self.assertEqual(one_label2count[1], 1)
        two_label2count = self._count_num_labels(task.outputs[2])
        self.assertEqual(two_label2count[0], 2) # last fraction are collected to the last output
        self.assertEqual(two_label2count[1], 1)
