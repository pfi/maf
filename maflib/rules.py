import copy
import json
import urllib
import maflib.core
import maflib.util

def download(url):
    """Rule to download a file from given URL.

    It stores the file to the target node.

    :param url: URL string of the file to be downloaded.
    :type url: ``str``
    :return: A rule.
    :rtype: :py:class:`maflib.core.Rule`

    """
    def body(task):
        urllib.urlretrieve(url, task.outputs[0].abspath())

    return maflib.core.Rule(fun=body, dependson=[download, url])


def max(key):
    """Creates an aggregator to select the max value of given key.

    The created aggregator chooses the result with the maximum value of
    ``key``, and writes the JSON object to the output node.

    :param key: A key to be used for selection of maximum value.
    :type key: ``str``
    :return: An aggregator.
    :rtype: :py:class:`maflib.core.Rule`

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
    @maflib.util.aggregator
    def body(values, outpath, parameter):
        min_value = None
        argmin = None
        for value in values:
            if min_value <= value[key]:
                continue
            min_value = value[key]
            argmin = value
        return json.dumps(argmin)

    return maflib.core.Rule(fun=body, dependson=[min, key])


@maflib.util.aggregator
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
    return json.dumps(scheme)


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


def calculate_stats_multilabel_classification(task):
    """Calculates various performance measure for multi-label classification.

    The "source" of this task is assumed to a json of a list, in which each
    item is a dictionary of the form ``{"p": 3, "c": 5}`` where ``"p"``
    indicates predict label, while "c" indicates the correct label. If you use
    libsvm, ``create_label_result_libsvm`` converts the results to this format.

    The output measures is summarized as follows, most of which are cited from (*):

    - Accuracy
    - AverageAccuracy
    - ErrorRate
    - Precision for each label
    - Recall for each label
    - F1 for each label
    - Specifity for each label
    - AUC for each label

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
        ...
        "2-precision": 0.6,
        "2-recall": 0.7,
        ...
      }

    where accuracy, average_accuracy and error_rate corresponds to Accuracy,
    AverageAccuracy and ErrorRate respectively. Average is macro average, which
    is consistent with the output of e.g., svm-predict. Other results (e.g.
    1-precision) are calculated for each label and represented as a pair of
    "label" and "result name" combined with a hyphen. For example, 1-precision
    is precision for the label 1, while 3-F1 is F1 for the label 3.

    (*) Marina Sokolova, Guy Lapalme
    A systematic analysis of performance measures for classification tasks
    Information Processing and Management 45 (2009) 427-437
    
    """
    def accuracy(labelstats):
        correct = 0
        for stat in labelstats.values():
            correct += stat["tp"]
        head_key = labelstats.keys()[0]
        n = sum(labelstats[head_key].values())
        return float(correct) / n
            
    def average_accuracy(labelstats):
        ret = 0
        for stat in labelstats.values():
            ret += float(stat["tp"] + stat["tn"]) \
                / (stat["tp"] + stat["fn"] + stat["fp"] + stat["tn"])
        return ret / float(len(labelstats))
    
    def error_rate(labelstats):
        ret = 0
        for stat in labelstats.values():
            ret += float(stat["fp"] + stat["fn"]) \
                / (stat["tp"] + stat["fn"] + stat["fp"] + stat["tn"])
        return ret / float(len(labelstats))
    
    def label_precision(stat):
        return float(stat["tp"]) / (stat["tp"] + stat["fp"])
    def label_recall(stat):
        return float(stat["tp"]) / (stat["tp"] + stat["fn"])
    def label_F1(stat):
        return float(2 * stat["tp"]) / (2 * stat["tp"] + stat["fn"] + stat["fp"])
    def label_specifity(stat):
        return float(stat["tn"]) / (stat["fp"] + stat["tn"])
    def label_AUC(stat):
        return 0.5 * (float(stat["tp"]) / (stat["tp"] + stat["fn"]) + \
                      float(stat["tn"]) / (stat["tn"] + stat["fp"]))
    
    predict_correct_labels = json.loads(task.inputs[0].read())
    labelstats = {}
    labelset = set()
    for e in predict_correct_labels:
        labelset.add(e["p"])
        labelset.add(e["c"])
    for label in labelset:
        labelstats[label] = {"tp": 0, # true positive
                             "tn": 0, # true negative
                             "fp": 0, # false positive
                             "fn": 0} # false negative
    for e in predict_correct_labels:
        p = e["p"]
        c = e["c"]
        for label, stat in labelstats.items():
            label_p = p == label
            label_c = c == label
            if label_p and label_c:
                stat["tp"] += 1
            elif label_p and not label_c:
                stat["fp"] += 1
            elif not label_p and label_c:
                stat["fn"] += 1
            else:
                stat["tn"] += 1
    
    results = {}
    results["accuracy"] = accuracy(labelstats)
    results["average_accuracy"] = average_accuracy(labelstats)
    results["error_rate"] = error_rate(labelstats)
    for label in labelset:
        results["%s-precision" % label] = label_precision(labelstats[label])
        results["%s-recall" % label] = label_recall(labelstats[label])
        results["%s-F1" % label] = label_F1(labelstats[label])
        results["%s-specifity" % label] = label_specifity(labelstats[label])
        results["%s-AUC" % label] = label_AUC(labelstats[label])
        
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
