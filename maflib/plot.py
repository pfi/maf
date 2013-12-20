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

# These two lines are necessary for desktop-enabled environment.
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot

import maflib.util

class PlotData:
    """Result of experimentation collected through a meta node to plot.

    Result of experiments is represented by a meta node consisted by a set of
    physical nodes each of which contains a dictionary or an array of
    dictionaries. This class is used to collect all dictionaries through the
    meta node and to extract point sequences to plot.

    """
    def __init__(self, inputs):
        """Constructs a plot data from a list of values to be plotted.

        :param inputs: A list of values to be plotted. The first argument of
            callback body function passed to
            :py:func:`maflib.util.aggregator` can be used for this
            argument.

        """
        self._inputs = inputs

    def get_data_1d(self, x, key=None, sort=True):
        """Extracts a sequence of one-dimensional data points.

        This function extracts x coordinate of each result value and creates a
        list of them. If sort == True, then the list is sorted. User can extract
        different sequences for varying values corresponding to given key(s).

        :param x: A key string corresponding to x coordinate.
        :type x: ``str``
        :param key: Key strings that define distinct sequences of data points.
            It can be either of None, a string value or a tuple of string
            values.
        :type key: None, ``str`` or tuple of strings
        :param sort: Flag for sorting the sequence(s).
        :type sort: ``bool``
        :return: If ``key`` is None, then it returns a list of x values.
            Otherwise, it returns a dictionary from key(s) to a sequence of x
            values. Each sequence consists of values matched to the key(s).
        :rtype: ``dict`` or ``list``

        """
        if key is None:
            xs = [value[x] for value in self._inputs if x in value]
            if sort:
                xs.sort()
            return xs

        data = {}
        for value in self._inputs:
            if x not in value:
                continue

            if isinstance(key, str):
                if key not in value:
                    continue
                key_value = value[key]
            else:
                key_value = tuple((value[k] for k in key if k in value))
                if len(key) != len(key_value):
                    continue

            if key_value not in data:
                data[key_value] = []

            data[key_value].append(value[x])

        if sort:
            for k in data:
                data[k].sort()

        return data

    def get_data_2d(self, x, y, key=None, sort=True):
        """Extracts a sequence of two-dimensional data points.

        See get_data_1d for detail. Difference from get_data_2d is that the
        values are represented by pairs.

        :param x: A key string corresponding to x (first) coordinate.
        :type x: ``str``
        :param y: A key string corresponding to y (second) coordinate.
        :type y: ``str``
        :param key: Key strings that define distinct sequences of data points.
            It can be either of None, a string value or a tuple of string
            values.
        :type key: None, ``str`` or tuple of strings
        :param sort: Flag for sorting the sequence(s).
        :type sort: ``bool``
        :return: If ``key`` is None, then it returns a pair of x value sequence
            and y value sequence. Otherwise, it returns a dictionary from a key
            to a pair of x value sequence and y value sequence. Each sequence
            consists of values matched to the key(s).
        :rtype: ``dict`` or ``tuple`` of two ``list`` s

        """
        if key is None:
            vals = [(value[x], value[y])
                    for value in self._inputs if x in value and y in value]
            if sort:
                vals.sort()
            return ([v[0] for v in vals], [v[1] for v in vals])

        data = {}
        for value in self._inputs:
            if x not in value or y not in value:
                continue

            if isinstance(key, str):
                if key not in value:
                    continue
                key_value = value[key]
            else:
                key_value = tuple((value[k] for k in key if k in value))
                if len(key) != len(key_value):
                    continue

            if key_value not in data:
                data[key_value] = []

            data[key_value].append((value[x], value[y]))

        for k in data:
            if sort:
                data[k].sort()
            data[k] = ([v[0] for v in data[k]], [v[1] for v in data[k]])

        return data

    def get_data_3d(self, x, y, z, key=None, sort=True):
        """Extracts a sequence of three-dimensional data points.

        See get_data_1d for detail. Difference from get_data_3d is that the
        values are represented by triples.

        :param x: A key string corresponding to x (first) coordinate.
        :type x: ``str``
        :param y: A key string corresponding to y (second) coordinate.
        :type y: ``str``
        :param z: A key string corresponding to z (third) coordinate.
        :type z: ``str``
        :param key: Key strings that define distinct sequences of data points.
            It can be either of None, a string value or a tuple of string
            values.
        :type key: None, ``str`` or tuple of strings
        :param sort: Flag for sorting the sequence(s).
        :type sort: ``bool``
        :return: If ``key`` is None, then it returns a triple of x value
            sequence, y value sequence and z value sequence. Otherwise, it
            returns a dictionary from a key to a triple of x value sequence, y
            value sequence and z value sequence. Each sequence consists of
            values matched to the key(s).
        :rtype: ``dict`` or ``tuple`` of three ``list`` s.

        """
        if key is None:
            vals = [(value[x], value[y], value[z])
                    for value in self._inputs
                    if x in value and y in value and z in value]
            if sort:
                vals.sort()
            return (
                [v[0] for v in vals],
                [v[1] for v in vals],
                [v[2] for v in vals])

        data = {}
        for value in self._inputs:
            if not (x in value and y in value and z in value):
                continue

            if isinstance(key, str):
                if key not in value:
                    continue
                key_value = value[key]
            else:
                key_value = tuple((value[k] for k in key if k in value))
                if len(key) != len(key_value):
                    continue

            if key_value not in data:
                data[key_value] = []

            data[key_value].append((value[x], value[y], value[z]))

        for k in data:
            if sort:
                data[k].sort()
            data[k] = (
                [v[0] for v in data[k]],
                [v[1] for v in data[k]],
                [v[2] for v in data[k]])

        return data


def plot_by(callback_body):
    """Creates an aggregator to plot data using matplotlib and PlotData.

    :param callback_body: Callable object or function that plots data. It takes
        three parameters: :py:class:`matplotlib.figure.Figure` object,
        :py:class:`maflib.plot.PlotData` object and a parameter of class
        :py:class:`maflib.core.Parameter`. User must define a callback function
        that plots given data to given figure.
    :type callback_body: ``function`` or callable object, whose signature is
        (:py:class:`matplotlib.figure.Figure`, :py:class:`PlotData`).

    """
    @functools.wraps(callback_body)
    @maflib.util.aggregator
    def callback(values, abspath, parameter):
        figure = matplotlib.pyplot.figure()
        plot_data = PlotData(values)
        callback_body(figure, plot_data, parameter)
        figure.savefig(abspath)
        return None

    return callback


def plot_line(x, y, legend=None):
    """Creates an aggregator that draw a line plot."""
    # TODO(beam2d): Write a document.

    def get_normalized_axis_config(k):
        if isinstance(k, str):
            return {'key': k}
        return k

    x = get_normalized_axis_config(x)
    y = get_normalized_axis_config(y)

    def callback(figure, data, parameter):
        axes = figure.add_subplot(111)

        if 'scale' in x:
            axes.set_xscale(x['scale'])
        if 'scale' in y:
            axes.set_yscale(y['scale'])
        axes.set_xlabel(x['key'])
        axes.set_ylabel(y['key'])

        if legend:
            legend_key = legend['key']
            labels = {}
            if 'labels' in legend:
                labels = legend['labels']
            key_to_xys = data.get_data_2d(x['key'], y['key'], key=legend_key)
            keys = sorted(key_to_xys.keys())

            for key in keys:
                xs, ys = key_to_xys[key]
                if key in labels:
                    label = labels[key]
                else:
                    label = '%s=%s' % (legend_key, key)
                # TODO(beam2d): Support marker.
                axes.plot(xs, ys, label=label)

            place = legend.get('loc', 'best')
            axes.legend(loc=place)
        else:
            xs, ys = data.get_data_2d(x['key'], y['key'])
            axes.plot(xs, ys)

    return plot_by(callback)
