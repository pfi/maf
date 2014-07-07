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

import collections
import copy
import json
import os.path
import tempfile
import urllib

import maflib.core
import maflib.util

def download(url, decompress_as=''):
    """Create a rule to download a file from given URL.

    It stores the file to the target node. If ``decompress_as`` is given, then
    it automatically decompresses the downloaded file.

    :param url: URL string of the file to be downloaded.
    :type url: ``str``
    :param decompress_as: Decompression method of downloaded file. If an empty
        string is given, then this function does not do decompression.
        ``'bz2'``, ``'gz'`` or ``'zip'`` is available.
    :return: A rule.
    :rtype: :py:class:`maflib.core.Rule`

    """
    def body(task):
        if decompress_as != '':
            t = tempfile.NamedTemporaryFile()
            urllib.urlretrieve(url, t.name)
            _decompress(t.name, task.outputs[0].abspath(), decompress_as)
        else:
            urllib.urlretrieve(url, task.outputs[0].abspath())

    return maflib.core.Rule(fun=body, dependson=[download, url])


def decompress(filetype='auto'):
    """A rule to decompress an input file.

    :param filetype: Type of compressed file. Following values are available.

        - ``'auto'``: Use automatically detected type from the extension of the
          input file name.
        - ``'bz2'``: bzip2 file.
        - ``'gz'``: gzip file.
        - ``'zip'``: zip file.
    :type filetype: ``str``
    :return: A rule.
    :rtype: :py:class:`maflib.core.Rule`

    """
    def body(task):
        ft = filetype
        if ft == 'auto':
            ft = os.path.splitext(task.inputs[0].abspath())[1][1:]

        res = _decompress(
            task.inputs[0].abspath(), task.outputs[0].abspath(), ft)
        if not res:
            raise Exception(
                "Filetype %s is not supported in decompress." % ft)

    return maflib.core.Rule(fun=body, dependson=[decompress, filetype])


def max(key):
    """Creates an aggregator to select the max value of given key.

    The created aggregator chooses the result with the maximum value of
    ``key``, and writes the JSON object to the output node.

    :param key: A key to be used for selection of maximum value.
    :type key: ``str``
    :return: An aggregator.
    :rtype: :py:class:`maflib.core.Rule`

    """
    @maflib.util.json_aggregator
    def body(values, outpath, parameter):
        if len(values) == 0:
            return json.dumps({})

        max_value = values[0][key]
        argmax = values[0]
        for value in values[1:]:
            if max_value < value[key]:
                max_value = value[key]
                argmax = value
        return argmax

    return maflib.core.Rule(fun=body, dependson=[max, key])


def min(key):
    """Creates an aggregator to select the minimum value of given key.

    The created aggregator chooses the result with the minimum value of
    ``key``, and writes the JSON object to the output node.

    :param key: A key to be used for selection of minimum value.
    :type key: ``str``
    :return: An aggregator.
    :rtype: :py:class:`maflib.core.Rule`

    """
    @maflib.util.json_aggregator
    def body(values, outpath, parameter):
        if len(values) == 0:
            return json.dumps({})

        min_value = values[0][key]
        argmin = values[0]
        for value in values[1:]:
            if min_value > value[key]:
                min_value = value[key]
                argmin = value
        return argmin

    return maflib.core.Rule(fun=body, dependson=[min, key])


@maflib.util.json_aggregator
def average(values, output, parameter):
    """Aggregator that calculates the average value for each key.

    The result contains all keys that some inputs contain. Each value is an
    average value of the corresponding key through all the inputs. If there
    is a value that cannot be passed to ``float()``, it omits the corresponding
    key from the result.

    """
    scheme = copy.deepcopy(values[0])
    for key in scheme:
        try:
            scheme[key] = sum(
                float(v[key]) for v in values) / float(len(values))
        except:
            pass
    return scheme


def convert_libsvm_accuracy(task):
    """Rule that converts message output by svm-predict into json file.

    This rule can be used to parse the output messsage of svm-predict command
    of LIBSVM, which contains an accuracy of prediction. The output is
    formatted like ``{"accuracy": <value>}``.

    :param task: waf task.
    :type task: :py:class:`waflib.Task.Task`

    """
    content = task.inputs[0].read()
    j = {'accuracy': float(content.split(' ')[2][:-1])}
    task.outputs[0].write(json.dumps(j))


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


def calculate_stats_multiclass_classification(task):
    """Calculates various performance measures for multi-class classification.

    The source of this task is assumed to be a json array each item of which
    is a dictionary of the form ``{"p": 3, "c": 5}`` where ``"p"`` indicates the
    predict label, while "c" indicates the correct label. If you use libsvm,
    ``create_label_result_libsvm`` converts the results to this format.

    The output measures is summarized as follows, most of which are cited from (*):

    Accuracy, AverageAccuray, ErrorRate

    Other measures:
      Precision, Recall, F1, Specifity and AUC
    are calculated for each label.

    In terms of Precision, Recall and F1, averaged results are also calculated.
    There are two different types of averaging: micro and macro.
    Micro average is calculated using global counts of true positive, false
    positive, etc, while macro average is calculated naively by dividing the
    number of labels.

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
    AverageAccuracy and ErrorRate respectively. Average is the macro average of
    all data, which is consistent with the output of e.g., svm-predict.
    Other results (e.g. 1-precision) are calculated for each label and represented
    as a pair of "label" and "measure" combined with a hyphen. For example,
    1-precision is the precision for the label 1, while 3-F1 is F1 for the label
    3.

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

        def precision(self):
            if self.precision_denom() == 0: return 1.0
            else: return float(self.precision_numer()) / self.precision_denom()
        def recall(self):
            if self.recall_denom() == 0: return 1.0
            else: return float(self.recall_numer()) / self.recall_denom()

        def specifity(self):
            if self.fp + self.tn == 0: return 1.0
            else: return float(self.tn) / (self.fp + self.tn)
        def AUC(self):
            a = 1.0 if self.tp == 0 else float(self.tp) / (self.tp + self.fn)
            b = 1.0 if self.tn == 0 else float(self.tn) / (self.tn + self.fp)
            return 0.5 * (a + b)
        def sum(self): return self.tp + self.fn + self.fp + self.tn
        def num_instance(self): return self.tp + self.fn

    def F1(prec, recall):
        if prec * recall == 0: return 0
        else: return 2 * prec * recall / (prec + recall)

    predict_correct_labels = json.loads(task.inputs[0].read())
    labelset = set([e["p"] for e in predict_correct_labels] \
                       + [e["c"] for e in predict_correct_labels])

    labelstats = collections.defaultdict(labelstat)
    for e in predict_correct_labels:
        p, c = e["p"], e["c"]
        for label in labelset:
            labelstats[label].add_count(p == label, c == label)

    def _macro_average(values):
        return float(sum(values)) / len(values)

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
    results["precision-macro"] = _macro_average([v for (k, v) in results.items() \
                                                     if k.endswith("precision")])
    results["precision-micro"] = float(sum([v.precision_numer() for v in labelstats.values()])) \
                               / sum([v.precision_denom() for v in labelstats.values()])
    results["precision-micro-numer"] = sum([v.precision_numer() for v in labelstats.values()])
    results["precision-micro-denom"] = sum([v.precision_denom() for v in labelstats.values()])
    results["recall-macro"] = _macro_average([v for (k, v) in results.items() \
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

        with open(task.outputs[0].abspath(), 'w') as train,\
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

def segment_without_label_bias(weights, extract_label=(lambda line: line[:line.find(' ')])):
    """Segments an example per line data into k-fold where k is the length of param weights.

    This method consider the label-bias when segmentation:
    In machine learning experiments, we often want to prepare training or testing examples
    in equal proportions for each label for the correct evaluation.
    ``weights`` specifies the proportion of examples in the k-th fold for each label.

    A typical usage of this task is as follows:

    .. code-block:: py

        exp(source='news20.scale',
            target='train dev test',
            rule=segment_without_label_bias([0.8, 0.1, 0.1]))

    This exp segment data news20.scale into 3-fold for train/develop/test.
    For each label, train contains 80% of the examples of that label, while dev/test contains
    10% of examples of the one.

    The input is assumed to be the format of an example per line, such as libsvm or vowpal format.
    The param ``extract_label`` specifies the way to extract the label from each line, so you can handle other format by customizing this function as far as it follows the one example per line format.

    :param weights: list of floats specifing the weight by which data are segmented
    :param extract_label: function extracting the label from an input line

    """

    def _segment_data_with_weights(data):
        normalized = map(lambda w: w / sum(weights), weights)
        accumulate = []
        a = 0
        for n in normalized:
            a += n
            accumulate.append(a)
        accumulate[len(accumulate) - 1] = 1.0
        endpoints = [0] + map(lambda w: int(len(data) * w), accumulate)
        return [data[endpoints[i]:endpoints[i + 1]] for i in range(len(endpoints) - 1)]

    def body(task):
        if len(weights) != len(task.outputs):
            raise maflib.core.InvalidMafArgumentException("lengths of weights must be the same as the number of target")

        label2examples = collections.defaultdict(list)
        for line in open(task.inputs[0].abspath()): label2examples[extract_label(line)].append(line)
        label2segmented_examples = dict([(k, _segment_data_with_weights(v)) \
                                   for k, v in label2examples.items()])
        for i, o in enumerate(task.outputs):
            with open(o.abspath(), 'w') as f:
                for examples in label2segmented_examples.values():
                    for line in examples[i]: f.write(line)
        return 0
    return maflib.core.Rule(body, dependson=[segment_without_label_bias])

def _decompress(srcpath, dstpath, filetype):
    if filetype == 'bz2':
        import bz2
        f = bz2.BZ2File(srcpath)
        decompressed_data = f.read()
        f.close()
    elif filetype == 'gz':
        import gzip
        with gzip.GzipFile(srcpath) as f:
            decompressed_data = f.read()
    elif filetype == 'zip':
        import zlib
        with open(srcpath) as f:
            compressed_data = f.read()
        decompressed_data = zlib.decompress(compressed_data)
    else:
        return False

    with open(dstpath, 'w') as f:
        f.write(decompressed_data)

    return True
