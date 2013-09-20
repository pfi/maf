import copy
import json
from collections import defaultdict
import maflib.core
import maflib.util

def max(key):
    """Creates an aggregator to select the max value of given key.

    The created aggregator chooses the result with the maximum value of
    ``key``, and writes the JSON object to the output node.

    :param key: A key to be used for selection of maximum value.
    :type key: ``str``
    :return: An aggregator.
    :rtype: ``function``

    """
    @maflib.util.aggregator
    def body(values, outpath, parameter):
        max_value = None
        argmax = None
        for value in values:
            if max_value >= value[key]:
                continue
            max_value = value[key]
            argmax = value
        return json.dumps(argmax)

    return body


def average():
    """Creates an aggregator that calculates the average value for each key.

    The result contains all keys that some inputs contain. Each value is an
    average value of the corresponding key through all the inputs. If there
    is a value that cannot be passed to ``float()``, it omits the corresponding
    key from the result.

    :return: An aggregator.
    :rtype: ``function``

    """
    # TODO(beam2d): This function can be a simple aggregator instead of
    # an aggregator generator.
    @maflib.util.aggregator
    def body(values, output, parameter):
        scheme = copy.deepcopy(values[0])
        for key in scheme:
            try:
                scheme[key] = sum(
                    float(v[key]) for v in values) / float(len(values))
            except:
                pass
        return json.dumps(scheme)

    return body


def convert_libsvm_accuracy(task):
    """Rule that converts message output by svm-predict into json file.

    This rule can be used to parse the output messsage of svm-predict command
    of LIBSVM, which contains an accuracy of prediction. The output is
    formatted like ``{"accuracy": <value>}``.

    :param task: waf task.
    :type task: :py:class:`waflib.Task.Task`
    :return: Zero.
    :rtype: ``int``

    """
    content = task.inputs[0].read()
    j = {'accuracy': float(content.split(' ')[2][:-1])}
    task.outputs[0].write(json.dumps(j))
    return 0


def create_label_result_libsvm(task):
    """TODO(noji) write document."""
    predict_f = task.inputs[0].abspath()
    test_f = task.inputs[1].abspath()
    labels = {}
    predict = [int(line.strip()) for line in open(predict_f)]
    correct = [int(line.strip().split(' ')[0]) for line in open(test_f)]
    if len(predict) != len(correct):
        raise maflib.core.InvalidMafArgumentException(
            "the number of lines of output file (%s) \
is not consistent with the one of test file (%s)." % (predict_f, test_f))
    instances = []
    for i in range(len(predict)):
        instances.append({"p": predict[i], "c": correct[i]})
    task.outputs[0].write(json.dumps(instances))
    return 0

def _weighted_average(num_examples, values):
    s = sum(num_examples)
    label_weight = map(lambda a: float(a) / s, num_examples)
    return sum([w * v for (w, v) in zip(label_weight, values)])

def _macro_average(values):
    return float(sum(values)) / len(values)
    
def calculate_stats_multiclass_classification(task):
    """Calculates various performance measure for multi-label classification.

    The "source" of this task is assumed to a json of a list, in which each
    item is a dictionary of the form ``{"p": 3, "c": 5}`` where ``"p"``
    indicates predict label, while "c" indicates the correct label. If you use
    libsvm, ``create_label_result_libsvm`` converts the results to this format.

    The output measures is summarized as follows, most of which are cited from (*):

    Accuracy, AverageAccuray, ErrorRate

    Other measures:
      Precision, Recall, F1, Specifity and AUC
    are calculated for each label.

    In terms of precision, Recall and F1, averaged results are also calculated.
    There are two different type of averaging: micro and macro.
    Micro average is calculated using global count of true positive, false positive, etc,
    while macro average is calculated naively by dividing the number of labels.

    The output of this task is one json file, like

    .. code-block:: javascript

      {
        "accuracy": 0.7,
        "average_accuracy": 0.8,
        "error_rate": 0.12,
        "1-precision": 0.5,
        "1-recall": 0.8,
        "1-F1": 0.6,
        "1-specifity": 0.6,
        "1-AUC": 0.7,
        "precision-micro":0.7
        "precision-macro":0.6
        ...
        "2-precision": 0.6,
        "2-recall": 0.7,
        ...
      }

    where accuracy, average_accuracy and error_rate corresponds to Accuracy,
    AverageAccuracy and ErrorRate respectively. Average is macro average of
    all data, which is consistent with the output of e.g., svm-predict.
    Other results (e.g. 1-precision) are calculated for each label and represented
    as a pair of "label" and "measure" combined with a hyphen. For example,
    1-precision is precision for the label 1, while 3-F1 is F1 for the label 3.

    (*) Marina Sokolova, Guy Lapalme
    A systematic analysis of performance measures for classification tasks
    Information Processing and Management 45 (2009) 427-437
    
    """
    class labelstat(object):
        def __init__(self):
            self.tp = 0  # true positive
            self.tn = 0  # true negative
            self.fp = 0  # false positive
            self.fn = 0  # false negative
            
        def add_count(self, is_predict_label, is_collect_label):
            if is_predict_label and is_collect_label: self.tp += 1
            elif is_predict_label and not is_collect_label: self.fp += 1
            elif not is_predict_label and is_collect_label: self.fn += 1
            else: self.tn += 1
            
        def accuracy(self): return float(self.tp + self.tn) / self.sum()
        def error_rate(self): return float(self.fp + self.fn) / self.sum()

        def precision_numer(self): return self.tp
        def precision_denom(self): return self.tp + self.fp
        def recall_numer(self): return self.tp
        def recall_denom(self): return self.tp + self.fn
        
        def precision(self): return float(self.precision_numer()) / self.precision_denom()
        def recall(self): return float(self.recall_numer()) / self.recall_denom()
        
        def specifity(self): return float(self.tn) / (self.fp + self.tn)
        def AUC(self):
            return 0.5 * (float(self.tp) / (self.tp + self.fn) + \
                          float(self.tn) / (self.tn + self.fp))
        def sum(self): return self.tp + self.fn + self.fp + self.tn
        def num_instance(self): return self.tp + self.fn

    def F1(prec, recall): return 2 * prec * recall / (prec + recall)
    
    predict_correct_labels = json.loads(task.inputs[0].read())
    labelset = set([e["c"] for e in predict_correct_labels])
    labelstats = defaultdict(labelstat)
    for e in predict_correct_labels:
        p, c = e["p"], e["c"]
        for label in labelset:
            labelstats[label].add_count(p == label, c == label)
    
    results = {}
    results["accuracy"] = \
        float(sum([s.tp for s in labelstats.values()])) / labelstats.values()[0].sum()
    results["average_accuracy"] = _macro_average([s.accuracy() for s in labelstats.values()])
    results["error_rate"] = _macro_average([s.error_rate() for s in labelstats.values()])

    for label, s in labelstats.items():
        prec = results["%s-precision" % label] = s.precision()
        recall = results["%s-recall" % label] = s.recall()
        results["%s-F1" % label] = F1(prec, recall)
        results["%s-specifity" % label] = s.specifity()
        results["%s-AUC" % label] = s.AUC()
    results["precision-macro"] = _macro_average([v for (k,v) in results.items() \
                                                     if k.endswith("precision")])
    results["precision-micro"] = float(sum([v.precision_numer() for v in labelstats.values()])) \
                               / sum([v.precision_denom() for v in labelstats.values()])
    results["recall-macro"] = _macro_average([v for (k,v) in results.items() \
                                                  if k.endswith("recall")])
    results["recall-micro"] = float(sum([v.recall_numer() for v in labelstats.values()])) \
                            / sum([v.recall_denom() for v in labelstats.values()])
    results["F1-macro"] = F1(results["precision-macro"], results["recall-macro"])
    results["F1-micro"] = F1(results["precision-micro"], results["recall-micro"])
    
    task.outputs[0].write(json.dumps(results))

def segment_by_line(num_folds, parameter_name='fold'):
    """Creates a rule that splits a line-by-line dataset to the k-th fold train
    and validation subsets for n-fold cross validation.

    Assume the input dataset is a text file where each sample is written in a
    distinct line. This task splits this dataset to given number of folds,
    extracts the n-th fold as a validation set (where n is specified by the
    parameter of given key), the others as a training set, and then writes
    these subsets to output nodes. This is a usual workflow of cross validation
    in machine learning.

    Note that this task does not shuffle the input dataset. If the order causes
    imbalancy of each fold, then user should add a task for shuffling the
    dataset before this task.

    This task requires a parameter indicating an index of the fold. The
    parameter name is specified by ``parameter_name``. The index must be a
    non-negative integer less than ``num_folds``.

    :param num_folds: Number of folds for splitting. Inverse of this value is
        the ratio of validation set size compared to the input dataset size. As
        noted above, the fold parameter must be less than ``num_folds``.
    :param parameter_name: Name of the parameter indicating the number of
        folds.
    :return: A rule.
    :rtype: ``function``

    """
    def body(task):
        source = open(task.inputs[0].abspath())
        num_lines = 0
        for line in source: num_lines += 1
        source.seek(0)

        base = num_lines / num_folds
        n = int(task.env[parameter_name])
        test_begin = base * n
        test_end = base * (n + 1)
        
        with open(task.outputs[0].abspath(), 'w') as train, \
             open(task.outputs[1].abspath(), 'w') as test:
            i = 0
            for line in source:
                if i < test_begin or i >= test_end:
                    # in train
                    train.write(line)
                else:
                    test.write(line)
                i += 1
        source.close()
    return body
