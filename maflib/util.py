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

import functools
import itertools
import json
import numpy.random
import types
import numpy as np

def aggregator(callback_body):
    """Creates an aggregator using function ``callback_body`` independent from
    waf.

    This function creates a wrapper of given callback function that behaves as
    a rule of an aggregation task. It supposes that input files are represented
    by JSON files each of which is a flat JSON object (i.e. an object that does
    not contain any objects) or a JSON array of flat objects. The created rule
    first combines these JSON objects into an array of Python dictionaries, and
    then passes it to the user-defined callback body.

    There are two ways to write the result to the output node. First is to let
    ``callback_body`` return the content string to be written to the output
    node; then the rule automatically writes it to the output node. Second is
    to let ``callback_body`` write it using its second argument (called
    ``abspath``), which is the absolute path to the output node. In this case,
    ``callback_body`` **MUST** return None to suppress the automatic writing.

    This function is often used as a decorator.
    See :py:mod:`maflib.rules` or :py:mod:`maflib.plot` to get
    examples of ``callback_body``.

    :param callback_body: A function or a callable object that takes three
        arguments: ``values``, ``abspath``, and ``parameter``. ``values`` is an
        array of dictionaries that represents the content of input files.
        ``abspath`` is an absolute path to the output node. ``parameter`` is
        the parameter of the output node, i.e. the parameter of this task. This
        function should return str or None.
    :type callback_body: ``function`` or callble object of signature
        ``(list, str)``.
    :return: An aggregator function that calls ``callback_body``.
    :rtype: ``function``

    """
    @functools.wraps(callback_body)
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
        result = callback_body(values, abspath, task.parameter)

        if result is not None:
            task.outputs[0].write(result)

    return callback


def product(parameter):
    """Generates a direct product of given listed parameters.

    Here is an example.

    .. code-block:: python

        maflib.util.product({'x': [0, 1, 2], 'y': [1, 3, 5]})
        # => [{'x': 0, 'y': 1}, {'x': 0, 'y': 3}, {'x': 0, 'y': 5},
        #     {'x': 1, 'y': 1}, {'x': 1, 'y': 3}, {'x': 1, 'y': 5},
        #     {'x': 2, 'y': 1}, {'x': 2, 'y': 3}, {'x': 2, 'y': 5}]
        # (the order of parameters may be different)

    :param parameter: A dictionary that represents a set of parameters. Its
        values are lists of values to be enumerated.
    :type parameter: ``dict`` from ``str`` to ``list``.
    :return: A direct product of a set of parameters.
    :rtype: ``list`` of ``dict``.

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

    :param num_samples: Number of samples. Resulting meta node contains this
        number of physical nodes for each input parameter set.
    :type num_samples: ``int``
    :param distribution: Dictionary from parameter names to values specifying
        distributions to sample from. Acceptable values are following:

        **Pair of numbers**
            ``(a, b)`` specifies a uniform distribution on the continuous
            interval [a, b).
        **List of values**
            This specifies a uniform distribution on the descrete set of
            values.
        **Callable object or function**
            ``f`` can be used for an arbitrary generator of values. Multiple
            calls of ``f()`` should generate random samples of user-defined
            distribution.
    :return: A list of sampled parameters.
    :rtype: ``list`` of ``dict``.

    """
    parameter_gens = {}
    keys = sorted(distribution)

    sampled = []
    for key in keys:
        # float case is specified by begin/end in a tuple.
        if isinstance(distribution[key], tuple):
            begin, end = distribution[key]
            begin = float(begin)
            end = float(end)
            # random_sample() generate a point from [0,1), so we scale and
            # shift it.
            gen = lambda: (end-begin) * numpy.random.random_sample() + begin

        # Discrete case is specified by a list
        elif isinstance(distribution[key], list):
            gen = lambda mult_ks=distribution[key]: mult_ks[
                numpy.random.randint(0,len(mult_ks))]

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

# Set the random seed of numpy to a fixed value.
# Without this, util.sample method generate different random numbers in each
# call, that is, we get a different parameter combination without any modify to
# the wscript. This is problematic when we add or remove snippets to the
# wscript; we don't want to re-run the experiments that have been already
# completed.
#
# WARNING: By fixing the random seed, we can control the generation of random
# numbers, but it is limited to some extent: if we add in wscript a experiment
# with util.sample above the previously defined experiment, which also use
# util.sample, generations of random number no longer follow the previous
# execution.
set_random_seed(10)
