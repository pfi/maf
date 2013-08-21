import itertools
import json
import types
import numpy as np

def create_aggregator(callback_body):
    """Creates an aggregator using function f independent from waf.

    Args:
        callback_body: Function or callable object that takes two arguments, a
        list of values to be aggregated and the absolute path to the output
        node. If this function returns string value, the value is written to the
        output node. If this function itself writes the result to the output
        file, it must return None.

    """
    def callback(task):
        values = []
        for node, parameter in zip(task.inputs, task.env.source_parameter):
            content = json.loads(node.read())
            if not isinstance(content, list):
                content = [content]
            for element in content:
                element.update(parameter)
            values += content

        abspath = task.outputs[0].abspath()
        result = callback_body(values, abspath)

        if result is not None:
            task.outputs[0].write(result)

    return callback


def product(parameter):
    """Generates direct product of given listed parameters. ::

        maf.product({'x': [0, 1, 2], 'y': [1, 3, 5]})
        # => [{'x': 0, 'y': 1}, {'x': 0, 'y': 3}, {'x': 0, 'y': 5},
              {'x': 1, 'y': 1}, {'x': 1, 'y': 3}, {'x': 1, 'y': 5},
              {'x': 2, 'y': 1}, {'x': 2, 'y': 3}, {'x': 2, 'y': 5}]
        # (the order of parameters may be different)

    """
    keys = sorted(parameter)
    values = [parameter[key] for key in keys]
    values_product = itertools.product(*values)
    return [dict(zip(keys, vals)) for vals in values_product]


def sample(num_samples, distribution):
    """Randomly samples parameters from given distributions.

    This function samples parameter combinations each of which is a dictionary
    from key to value sampled from a distribution corresponding to the key.
    It is useful for hyper-parameter optimization compared to using ``product``,
    since every instance can be different on all dimensions for each other.

    Args:
        num_samples: Number of samples. Resulting meta node contains this number
            of physical nodes for each input parameter set.
        distribution: Dictionary from parameter names to values specifying
            distributions to sample from. Acceptable values are following:

            **Pair of numbers** ``(a, b)`` specifies a uniform distribution on
                the continuous interval [a, b].
            **List of values** specifies a uniform distribution on the descrete
                set of values.
            **Callbable object or function** ``f`` can be used for an arbitrary
                generator of values. Multiple calls of ``f()`` should generate
                random samples of user-defined distribution.

    """
    parameter_gens = {}
    keys = sorted(distribution)

    sampled = []
    for key in keys:
        # float case is specified by begin/end in a tuple.
        if isinstance(distribution[key], tuple):
            begin, end = distribution[key]
            if isinstance(begin, float) or isinstance(end, float):
                begin = float(begin)
                end = float(end)
                # random_sample() generate a point from [0,1), so we scale and
                # shift it.
                gen = lambda: (end-begin) * np.random.random_sample() + begin

        # Discrete case is specified by a list
        elif isinstance(distribution[key], list):
            gen = lambda mult_ks=distribution[key]: mult_ks[
                np.random.randint(0,len(mult_ks))]

        # Any random generating function
        elif isinstance(distribution[key], types.FunctionType):
            gen = distribution[key]

        else:
            gen = lambda: distribution[key] # constant

        parameter_gens[key] = gen

    for i in range(num_samples):
        instance = {}
        for key in keys:
            instance[key] = parameter_gens[key]()
        sampled.append(instance)

    return sampled

def set_random_seed(x):
    np.random.seed(x)

set_random_seed(10)
