from collections import defaultdict
import copy
import itertools
import json
import os
import os.path
try:
    import cPickle as pickle
except ImportError:
    import pickle

from matplotlib import pyplot
from waflib.Build import BuildContext
import waflib.Utils

# TODO(beam2d): Add tests.
# TODO(beam2d): Separate this file.

def options(opt):
    pass

def configure(conf):
    pass

class ExperimentContext(BuildContext):
    """
    Context class of waf experiment (a.k.a. maf).
    """

    cmd = 'experiment'
    fun = 'experiment'
    variant = 'experiment'

    def __init__(self, **kw):
        super(ExperimentContext, self).__init__(**kw)
        self._experiment_graph = ExperimentGraph()

        # Callback registered by BuildContext.add_pre_fun is called right after
        # all wscripts are executed.
        super(ExperimentContext, self).add_pre_fun(
            ExperimentContext._process_call_objects)

    def __call__(self, **kw):
        """
        Main method to generate tasks.

        TODO(beam2d): Add more description.
        """

        call_object = CallObject(**kw)
        self._experiment_graph.add_call_object(call_object)

    @staticmethod
    def _process_call_objects(self):
        """
        Callback function called right after all wscripts are executed.

        This function virtually generates all task generators under
        ExperimentContext.
        """

        # Run topological sort on dependency graph.
        call_objects = self._experiment_graph.get_sorted_call_objects()

        # TODO(beam2d): Remove this stub file name.
        self._parameter_id_generator = ParameterIdGenerator(
            'build/experiment/.maf_id_table')
        self._nodes = defaultdict(set)

        try:
            for call_object in call_objects:
                self._process_call_object(call_object)
        finally:
            self._parameter_id_generator.save()

    def _process_call_object(self, call_object):
        if 'rule' in call_object.__dict__ and not isinstance(call_object.rule, str):
            # Callable object other than function is not allowed as a rule in
            # waf. Here we relax this restriction.
            rule_impl = call_object.rule
            call_object.rule = lambda task: rule_impl(task)

        if 'for_each' in call_object.__dict__:
            self._generate_aggregation_tasks(call_object)
        else:
            self._generate_tasks(call_object)

    def _generate_tasks(self, call_object):
        if not call_object.source:
            for parameter in call_object.parameters:
                self._generate_task(call_object, [], parameter)

        parameter_lists = []

        # Generate all valid list of parameters corresponding to source nodes.
        for node in call_object.source:
            node_params = self._nodes[node]
            if not node_params:
                # node is physical. We use empty parameter as a dummy.
                node_params = {Parameter()}

            if not parameter_lists:
                # First node
                for node_param in node_params:
                    parameter_lists.append([node_param])
                continue

            new_lists = []
            for node_param in node_params:
                for parameter_list in parameter_lists:
                    if any(p.conflict_with(node_param) for p in parameter_list):
                        continue
                    new_list = list(parameter_list)
                    new_list.append(node_param)
                    new_lists.append(new_list)

            parameter_lists = new_lists

        for parameter_list in parameter_lists:
            for parameter in call_object.parameters:
                if any(p.conflict_with(parameter) for p in parameter_list):
                    continue
                self._generate_task(call_object, parameter_list, parameter)

    def _generate_task(self, call_object, source_parameter, parameter):
        # Create target parameter by merging source parameter and task-gen
        # parameter.
        target_parameter = Parameter()
        for p in source_parameter:
            target_parameter.update(p)
        target_parameter.update(parameter)

        for node in call_object.target:
            self._nodes[node].add(target_parameter)

        # Convert source/target meta nodes to physical nodes.
        physical_source = self._resolve_meta_nodes(
            call_object.source, source_parameter)
        physical_target = self._resolve_meta_nodes(
            call_object.target, target_parameter)

        # Create arguments of BuildContext.__call__.
        physical_call_object = copy.deepcopy(call_object)
        physical_call_object.source = physical_source
        physical_call_object.target = physical_target
        del physical_call_object.parameters

        self._call_super(
            physical_call_object, source_parameter, target_parameter)

    def _generate_aggregation_tasks(self, call_object):
        # In aggregation tasks, source and target must be only one (meta) node.
        # Source node must be meta node. Whether target node is meta or not is
        # automatically decided by source parameters and for_each keys.
        if not call_object.source or len(call_object.source) > 1:
            raise InvalidMafArgumentException(
                "'source' in aggregation must include only one meta node")
        if not call_object.target or len(call_object.target) > 1:
            raise InvalidMafArgumentException(
                "'target' in aggregation must include only one meta node")

        source_node = call_object.source[0]
        target_node = call_object.target[0]

        source_parameters = self._nodes[source_node]
        # Mapping from target parameter to list of source parameter.
        target_to_source = defaultdict(set)

        for source_parameter in source_parameters:
            target_parameter = Parameter(
                [(key, source_parameter[key]) for key in call_object.for_each])
            target_to_source[target_parameter].add(source_parameter)

        for target_parameter in target_to_source:
            source_parameter = target_to_source[target_parameter]
            source = [self._resolve_meta_node(source_node, parameter)
                      for parameter in source_parameter]
            target = self._resolve_meta_node(target_node, target_parameter)

            self._nodes[target_node].add(target_parameter)

            # Create arguments of BuildContext.__call__.
            physical_call_object = copy.deepcopy(call_object)
            physical_call_object.source = source
            physical_call_object.target = target
            del physical_call_object.for_each

            self._call_super(
                physical_call_object, source_parameter, target_parameter)

    def _call_super(self, call_object, source_parameter, target_parameter):
        taskgen = super(ExperimentContext, self).__call__(
            **call_object.__dict__)
        taskgen.env.source_parameter = source_parameter
        taskgen.env.update(target_parameter.to_str_valued_dict())

    def _resolve_meta_nodes(self, nodes, parameters):
        if not isinstance(parameters, list):
            parameters = [parameters] * len(nodes)

        physical_nodes = []
        for node, parameter in zip(nodes, parameters):
            physical_nodes.append(self._resolve_meta_node(node, parameter))
        return physical_nodes

    def _resolve_meta_node(self, node, parameter):
        if parameter:
            parameter_id = self._parameter_id_generator.get_id(parameter)
            node = os.path.join(
                node, '-'.join([parameter_id, os.path.basename(node)]))
        if node[0] == '/':
            return self.root.find_resource(node)
        return self.path.find_or_declare(node)

# Maf utility library

# Aggregators

def create_aggregator(callback_body):
    """
    Creates an aggregator using function f independent from waf.

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

def max(key):
    """
    Gets an aggregator to select max value of given key.
    """
    def body(values, outpath):
        max_value = None
        argmax = None
        for value in values:
            if max_value >= value[key]:
                continue
            max_value = value[key]
            argmax = value
        return json.dumps(argmax)

    return create_aggregator(body)

# Plotting

class PlotData:
    """
    Result of experimentation collected through a meta node to plot.

    Result of experiments is represented by a meta node consisted by a set of
    physical nodes each of which contains a dictionary or an array of
    dictionaries. This class is used to collect all dictionaries through the
    meta node and to extract point sequences to plot.
    """

    def __init__(self, inputs):
        """
        Constructs a plot data from a list of values to be plotted.

        Args:
            inputs: A list of values to be plotted. The first argument of
            callback body function passed to ``create_aggregator`` can be used
            for this ``inputs`` argument.
        """
        self._inputs = inputs

    def get_data_1d(self, x, key=None, sort=True):
        """
        Extracts a sequence of one-dimensional data points.

        This function extracts x coordinate of each result value and creates a
        list of them. If sort == True, then the list is sorted. User can extract
        different sequences for varying values corresponding to given key(s).

        Args:
            x: A key string corresponding to x coordinate.
            key: Key strings that define distinct sequences of data points.
                It can be either of None, a string value or a tuple of string
                values.
            sort: Flag for sorting the sequence(s).

        Returns:
            If ``key`` is None, then it returns a list of x values. Otherwise,
            it returns a dictionary from key(s) to a sequence of x values.
            Each sequence consists of values matched to the key(s).
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
        """
        Extracts a sequence of two-dimensional data points.

        See get_data_1d for detail. Difference from get_data_2d is that the
        values are represented by pairs.

        Args:
            x: A key string corresponding to x (first) coordinate.
            y: A key string corresponding to y (second) coordinate.
            key: Key strings that define distinct sequences of data points.
                It can be either of None, a string value or a tuple of string
                values.
            sort: Flag for sorting the sequence(s).

        Returns:
            If ``key`` is None, then it returns a list of (x, y) pairs.
            Otherwise, it returns a dictionary from key(s) to a sequence of
            (x, y) pairs. Each sequence consists of values matched to the
            key(s).
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
        """
        Extracts a sequence of three-dimensional data points.

        See get_data_1d for detail. Difference from get_data_3d is that the
        values are represented by triples.

        Args:
            x: A key string corresponding to x (first) coordinate.
            y: A key string corresponding to y (second) coordinate.
            z: A key string corresponding to z (third) coordinate.
            key: Key strings that define distinct sequences of data points.
                It can be either of None, a string value or a tuple of string
                values.
            sort: Flag for sorting the sequence(s).

        Returns:
            If ``key`` is None, then it returns a list of (x, y, z) triples.
            Otherwise, it returns a dictionary from key(s) to a sequence of
            (x, y, z) triples. Each sequence consists of values matched to the
            key(s).
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
    """
    Creates an aggregator to plot data using matplotlib and PlotData.

    Args:
        callback_body: Callable object or function that plots data. It takes
            two parameters: matplotlib.figure.Figure object and PlotData object.
            User must define a callback function that plots given data to given
            figure.
    """
    def callback(values, abspath):
        figure = pyplot.figure()
        plot_data = PlotData(values)
        callback_body(figure, plot_data)
        figure.savefig(abspath)
        return None

    return create_aggregator(callback)

def plot_line(x, y, legend=None):
    """
    Creates an aggregator that draw a line plot.

    TODO(beam2d): Write a document.
    """
    def get_normalized_axis_config(k):
        if isinstance(k, str):
            return {'key': k}
        return k

    x = get_normalized_axis_config(x)
    y = get_normalized_axis_config(y)

    def callback(figure, data):
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

            place = legend.get('loc', 'lower right')
            axes.legend(loc=place)
        else:
            xs, ys = data.get_data_2d(x['key'], y['key'])
            axes.plot(xs, ys)

    return plot_by(callback)

# Convenient rules

def convert_libsvm_accuracy(task):
    """
    Rule that converts message output by svm-predict into json file.
    """

    content = task.inputs[0].read()
    j = {'accuracy': float(content.split(' ')[2][:-1])}
    task.outputs[0].write(json.dumps(j))
    return 0

# Parameter generation

def product(parameter):
    """
    Generate direct product of given listed parameter. ::

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
    """
    Randomly samples parameters from given distributions.

    This function samples parameter combinations each of which is a dictionary
    from key to value sampled from a distribution corresponding to the key.
    It is useful for hyper-parameter optimization compared to using ``product``,
    since every instance is different on all dimensions for each other.

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
            begin,end = distribution[key]
            if isinstance(begin, float) or isinstance(end, float):
                begin = float(begin)
                end = float(end)
                # random_sample() generate a point from [0,1), so we scale and
                # shift it.
                gen = lambda: (end-begin) * np.random.random_sample() + begin

        # Discrete case is specified by a list
        elif isinstance(distribution[key], list):
            gen = lambda mult_ks=distribution[key]:
                mult_ks[np.random.randint(0,len(mult_ks))]

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

# Maf internal library

class CyclicDependencyException(Exception):
    """
    Exception raised when experiment graph has a cycle.
    """
    pass

class InvalidMafArgumentException(Exception):
    """
    Exception raised when arguments of ExperimentContext.__call__ is wrong.
    """
    pass

class Parameter(dict):
    """
    Parameter of maf task.

    This is a dict with hash(). Be careful to use it with set(); parameter has
    hash(), but is mutable.
    """

    def __hash__(self):
        # TODO(beam2d): Should we cache this value?
        return hash(frozenset(self.iteritems()))

    def conflict_with(self, parameter):
        """
        Checks whether the parameter conflicts with given other parameter.

        Returns:
           True if self conflicts with parameter, i.e. contains different values
           corresponding to same key.
        """
        common_keys = set(self) & set(parameter)
        return any(self[key] != parameter[key] for key in common_keys)

    def to_str_valued_dict(self):
        """
        Gets dictionary with same key and value of type str.
        """
        return dict([(k, str(self[k])) for k in self])

class CallObject(object):
    """
    Object representing one call of ExperimentContext.__call__()
    """

    def __init__(self, **kw):
        """
        Initializes a call object. kw['source'] and kw['target'] are converted
        into list of strings.

        Args:
            **kw: Arguments of ``ExperimentContext.__call__``.
        """
        self.__dict__.update(kw)

        _let_element_to_be_list(self.__dict__, 'source')
        _let_element_to_be_list(self.__dict__, 'target')
        if 'for_each' in self.__dict__:
            _let_element_to_be_list(self.__dict__, 'for_each')

        if 'parameters' not in self.__dict__:
            self.parameters = [Parameter()]

class ExperimentGraph(object):
    """
    Bipartite graph consisting of meta node and call object node.
    """

    def __init__(self):
        self._edges = defaultdict(set)
        self._call_objects = []

    def add_call_object(self, call_object):
        """
        Adds call object node, related meta nodes and edges.

        Args:
            call_object: Call object to be added.
        """
        index = len(self._call_objects)
        self._call_objects.append(call_object)

        for in_node in call_object.source:
            self._edges[in_node].add(index)

        for out_node in call_object.target:
            self._edges[index].add(out_node)

    def get_sorted_call_objects(self):
        """
        Runs topological sort on the experiment graph and returns a sorted list
        of call objects.
        """

        nodes = self._collect_independent_nodes()
        edges = copy.deepcopy(self._edges)

        reverse_edges = defaultdict(set)
        for node in edges:
            edge = edges[node]
            for tgt in edge:
                reverse_edges[tgt].add(node)

        # Topological sort
        ret = []
        while nodes:
            node = nodes.pop()
            if isinstance(node, int):
                # node is a name of call object
                ret.append(self._call_objects[node])

            edge = edges[node]
            for dst in edge:
                reverse_edges[dst].remove(node)
                if not reverse_edges[dst]:
                    nodes.add(dst)
                    del reverse_edges[dst]
            del edges[node]

        if edges:
            raise CyclicDependencyException()

        return ret

    def _collect_independent_nodes(self):
        nodes = set(self._edges)
        for node in self._edges:
            nodes -= self._edges[node]
        return nodes

class ParameterIdGenerator(object):
    """
    Maintainer of correspondences between parameters and physical node names.

    Meta node has a path and its own parameters, each of which corresponds to
    one physical waf node named as 'path/N', where N is a unique name of the
    parameter. The correspondence between parameter and its name must be
    consistent over multiple execution of waf, so we serializes the table to
    hidden file.

    NOTE: On exception raised during task generation, save() must be called
    to avoid inconsistency on node names that had been generated before the
    exception was raised.

    Attributes:
        path: Path to file that the table is serialized at.
    """

    def __init__(self, path):
        """
        Initializes the resolver.

        Args:
            path: Path to persistent file of the table.
        """
        # TODO(beam2d): Isolate persistency support from resolver.

        self.path = path

        if os.path.exists(path):
            with open(path) as f:
                self._table = pickle.load(f)
        else:
            self._table = {}

    def save(self):
        """
        Serializes the table to the file at self.path.
        """
        with _create_file(self.path) as f:
            pickle.dump(self._table, f)

    def get_id(self, parameter):
        """
        Gets the id of given parameter.

        Args:
            parameter: Parameter object.

        Returns:
            Id of given parameter. The id may be generated in this method if
            necessary.
        """

        if parameter in self._table:
            return self._table[parameter]

        new_id = str(len(self._table))
        self._table[parameter] = new_id

        return new_id

def _create_file(path):
    """
    Opens file in write mode. It also creates intermediate directories if
    necessary.
    """
    prefixes = []
    cur_dir = path
    while cur_dir:
        cur_dir = os.path.dirname(cur_dir)
        prefixes.append(cur_dir)
    prefixes.reverse()

    for prefix in prefixes:
        if prefix and not os.path.exists(prefix):
            os.mkdir(prefix)

    return open(path, 'w')

def _get_list_from_kw(kw, key):
    if key in kw:
        return waflib.Utils.to_list(kw[key])
    return []

def _let_element_to_be_list(d, key):
    if key not in d:
        d[key] = []
    if isinstance(d[key], str):
        d[key] = waflib.Utils.to_list(d[key])

def _synchronized_sort(l1, l2):
    pairs = sorted(zip(l1, l2))
    return ([p[0] for p in pairs], [p[1] for p in pairs])
