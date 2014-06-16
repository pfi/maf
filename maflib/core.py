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

"""
A core of maf - an environment for computational experimentations on waf.

This module contains the core functionality of maf that handles parameterized
tasks and metanodes.
"""

import collections
import copy
import os
import os.path
import types
import inspect
import re
import tempfile
import subprocess
try:
    import cPickle as pickle
except ImportError:
    import pickle

import waflib.Build
import waflib.Utils
import waflib.Options
from waflib.TaskGen import before_method, feature


def options(opt):
    pass


def configure(conf):
    pass


class ExperimentContext(waflib.Build.BuildContext):
    """Context class of waf experiment (a.k.a. maf)."""

    def __init__(self, **kw):
        super(ExperimentContext, self).__init__(**kw)
        self._experiment_graph = ExperimentGraph()

        # Callback registered by BuildContext.add_pre_fun is called right after
        # all wscripts are executed.
        super(ExperimentContext, self).add_pre_fun(
            ExperimentContext._process_call_objects)

    def __call__(self, **kw):
        """Main method to generate tasks."""

        if 'rule' not in kw:
            # Workaround for non-experimental tasks
            # TODO(beam2d): Integrate non-/experimental tasks
            super(ExperimentContext, self).__call__(**kw)
        else:
            call_object = CallObject(wscript=self.cur_script, **kw)
            self._experiment_graph.add_call_object(call_object)

    def _process_call_objects(self):
        """Callback function called right after all wscripts are executed.

        This function virtually generates all task generators under
        ExperimentContext.

        """
        # Run topological sort on dependency graph.
        call_objects = self._experiment_graph.get_sorted_call_objects()

        table_path = os.path.join(self.variant_dir, '.maf_id_table')
        self._parameter_id_generator = ParameterIdGenerator(
            table_path, table_path + '.tsv')
        self._nodes = collections.defaultdict(set)

        try:
            for call_object in call_objects:
                self._process_call_object(call_object)
        finally:
            self._parameter_id_generator.save()

    def _process_call_object(self, call_object):
        self._set_rule_and_dependson(call_object)

        if hasattr(call_object, 'for_each'):
            self._generate_aggregation_tasks(call_object, 'for_each')
        elif hasattr(call_object, 'aggregate_by'):
            self._generate_aggregation_tasks(call_object, 'aggregate_by')
        else:
            self._generate_tasks(call_object)

    def _set_rule_and_dependson(self, call_object):
        # dependson attribute is a variable or a function, changes of which
        # will be automatically traced; this is set by two ways:
        #  1) write dependson attribute in wscript
        #  2) give rule in Rule object having non-empty dependson
        rule = call_object.rule
        if 'rule' in call_object.__dict__ and not isinstance(rule, str):
            if not isinstance(rule, Rule):
                rule = Rule(rule)
            rule.add_dependson(getattr(call_object, 'dependson', []))
            call_object.rule = lambda task: rule.fun(task)
            call_object.dependson = rule.stred_dependson()
        else:
            call_object.dependson = []

    def _generate_tasks(self, call_object):
        if not call_object.rel_source:
            for parameter in call_object.parameters:
                self._generate_task(call_object, [], parameter)

        parameter_lists = []

        # Generate all valid list of parameters corresponding to source nodes.
        for node in call_object.rel_source:
            node_params = self._nodes[node]
            if not node_params:
                # node is physical. We use empty parameter as a dummy.
                node_params = [Parameter()]

            if not parameter_lists:
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

        for node in call_object.rel_target:
            self._nodes[node].add(target_parameter)

        # Convert source/target meta nodes to physical nodes.
        physical_source = self._resolve_meta_nodes(
            call_object.rel_source, source_parameter)
        physical_target = self._resolve_meta_nodes(
            call_object.rel_target, target_parameter)

        # Create arguments of BuildContext.__call__.
        physical_call_object = copy.deepcopy(call_object)
        physical_call_object.source = physical_source
        physical_call_object.target = physical_target
        del physical_call_object.parameters

        self._call_super(
            physical_call_object, source_parameter, target_parameter)

    def _generate_aggregation_tasks(self, call_object, key_type):
        # In aggregation tasks, source and target must be only one (meta) node.
        # Source node must be meta node. Whether target node is meta or not is
        # automatically decided by source parameters and for_each/aggregate_by
        # keys.
        if not call_object.source or len(call_object.source) > 1:
            raise InvalidMafArgumentException(
                "'source' in aggregation must include only one meta node")
        if not call_object.target or len(call_object.target) > 1:
            raise InvalidMafArgumentException(
                "'target' in aggregation must include only one meta node")

        source_node = call_object.rel_source[0]
        target_node = call_object.rel_target[0]

        source_parameters = self._nodes[source_node]
        # Mapping from target parameter to list of source parameter.
        target_to_source = collections.defaultdict(list)

        for source_parameter in source_parameters:
            target_parameter = Parameter()
            if key_type == 'for_each':
                for key in call_object.for_each:
                    target_parameter[key] = source_parameter[key]
            elif key_type == 'aggregate_by':
                for key in source_parameter:
                    if key not in call_object.aggregate_by:
                        target_parameter[key] = source_parameter[key]
            target_to_source[target_parameter].append(source_parameter)

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
            if key_type == 'for_each':
                del physical_call_object.for_each
            else:
                del physical_call_object.aggregate_by

            self._call_super(
                physical_call_object, source_parameter, target_parameter)

    def _call_super(self, call_object, source_parameter, target_parameter):
        taskgen = super(ExperimentContext, self).__call__(
            **call_object.__dict__)
        taskgen.env.source_parameter = source_parameter  # for backward compatibility
        taskgen.env.update(target_parameter.to_str_valued_dict())

        depkeys = [('dependson%d' % i) for i in range(len(call_object.dependson))]
        taskgen.env.update(dict(zip(depkeys, call_object.dependson)))

        taskgen.parameter = target_parameter
        taskgen.source_parameter = source_parameter

    def _resolve_meta_nodes(self, nodes, parameters):
        if not isinstance(parameters, list):
            parameters = [parameters] * len(nodes)

        physical_nodes = []
        for node, parameter in zip(nodes, parameters):
            physical_nodes.append(self._resolve_meta_node(node, parameter))
        return physical_nodes

    def _resolve_meta_node(self, node, parameter):
        def _not_deleted_any_files_in(n):
            children = getattr(n, 'children', {})
            if not children:
                return os.path.exists(n.abspath())
            else:
                return all([_not_deleted_any_files_in(c) for c in n.children.values()])
                    
        if parameter:
            parameter_id = self._parameter_id_generator.get_id(parameter)
            node = os.path.join(
                node, '-'.join([parameter_id, os.path.basename(node)]))
        if node[0] == '/':
            # find_node can find directories (compared to find_resource, which can only find files)
            return self.root.find_node(node) 

        # Currently, the below contains some tricks for supporting directory
        # metanodes; Suppose node represent a metanode that is a directory on
        # the filesystem. When we search this node by ``find_or_declare``, we
        # can get that node object, but ``find_or_declare`` overwrites the sig
        # property of found node with None. This sig property will be used when
        # deciding whether run or not current task, and if sig is set None,
        # the task is always run. See:
        # http://docs.waf.googlecode.com/git/apidocs_17/_modules/waflib/Node.html#Node.find_or_declare
        # To avoid this problem, we first run search_node to find directory meta
        # node. If this is failed, normal search with find_or_declare will be run.
        existing_dir_node = self.path.get_bld().search_node(node)

        # search_node doesn't look on filesystem, so cannot detect manual changes on
        # the directory; e.g., sometimes one may delete an output directory or figure
        # manually. `_not_deleted_any_files_in` check the consistency on the filesystem.
        if existing_dir_node and _not_deleted_any_files_in(existing_dir_node):
            return existing_dir_node
        else:
            return self.path.find_or_declare(node)


class GraphContext(ExperimentContext):
    '''outputs a graph of dependencies between tasks'''
    
    cmd = 'graph'

    def node_label(self, node):
        parameter_id = self._extract_parameter_id(node)
        if parameter_id == -1:
            return ""

        if waflib.Options.options.simple_param:
            return str(parameter_id)
        else:
            parameter = self._parameter_id_generator.get(parameter_id)
            return "\\n".join(['%s: %s' % (k, v) for (k, v) in parameter.items()])

    class NodeIndexer(object):
        """Indexer assigning a unique id to each Node instance.

        Because each Node instance has a unique absolute path, Node -> id mappings
        are managed with a dictionary of type `dict(str, id)` preserving
        correspondences between a path to an id.
        
        """
        
        def __init__(self):
            self.path2id = {}
            self.nodes = []
            
        def get_id(self, node):
            path = node.abspath()
            if path in self.path2id:
                return self.path2id[path]
            else:
                node_id = len(self.nodes)
                self.path2id[path] = node_id
                self.nodes.append(node)
                return node_id
            
        def get(self, node_id):
            return self.nodes[node_id]
            
    class MetaNodes(object):
        """A collection of meta nodes.

        This class essentially is a hashtable preserving a collection of node ids
        sharing the same meta node signature. Meta node signature is calculated
        by :py:func:`GraphContext._extract_meta_node`.
        
        """
        
        def __init__(self, unique_nodes):
            self.table = collections.defaultdict(set) # meta node signature -> node ids
            for i, node in enumerate(unique_nodes):
                self.add_node(node, i)
            
        def add_node(self, node, id):
            meta = GraphContext._extract_meta_node(node)
            self.table[meta].add(id)

        def render_graphviz(self, node_indexer, ctx):
            lines = []
            
            for i, (meta_sig, node_ids) in enumerate(self.table.items()):
                lines.append("subgraph cluster_meta_node" + str(i) + " {")
                lines.append('label="%s"' % meta_sig)
                for node_id in node_ids:
                    node = node_indexer.get(node_id)
                    lines.append('node%s[label="%s" style=filled fillcolor=white]' %
                                 (node_id, ctx.node_label(node)))
                lines.append("}")
                
            return "\n".join(lines)
            
    class MetaTasks(object):
        """A collection of meta classes similar to MetaNodes."""

        num_invis_around_task = 3
        max_num_invis = 10      # num of invis nodes does not exceed this
        num_invis_per_nodes = 3 # num of invis nodes =
                                #  (sum of input or output nodes) / num_invis_per_nodes
        
        def __init__(self, tasks):
            self.tasks = list(tasks)
            self.table = collections.defaultdict(set) # meta task signature -> task ids
            for i, task in enumerate(tasks):
                self.add_task(task, i)
            
        def add_task(self, task, id):
            task_sig = "".join([GraphContext._extract_meta_node(n) for n
                                in _to_list(task.source) + _to_list(task.target)])
            self.table[task_sig].add(id)

        def render_graphviz(self):
            lines = []
            self.invis_i = 0 # used to distinguish all invisible points around a task
            def add_invis_points():
                for i in range(self.num_invis_around_task):
                    lines.append("task_invis%d[style=invis,shape=point]" %
                                 self.invis_i)
                    self.invis_i += 1

            for i, (meta_sig, task_ids) in enumerate(self.table.items()):
                lines.append("subgraph cluster_meta_task" + str(i) + " {")
                lines.append("style=filled;")
                lines.append("color=lightgrey;")
                add_invis_points()
                for task_id in task_ids:
                    lines.append("task%d[shape=point,style=filled,color=black]" %
                                 (task_id))
                    add_invis_points()
                lines.append("}")
                
            return "\n".join(lines)

        def render_invisibles(self, node_indexer):
            self.invis_i = 0 # used to distinguish all invisible points between nodes
            
            def num_in_links(meta):
                return sum([len(_to_list(self.tasks[task_id].source))
                            for task_id in self.table[meta]])
            def num_out_links(meta):
                return sum([len(_to_list(self.tasks[task_id].target))
                            for task_id in self.table[meta]])

            def extract_meta_links(meta_task, source=True):
                links = []
                existing_meta_nodes = set()
                for task_id in self.table[meta_task]:
                    task = self.tasks[task_id]
                    for node in _to_list(task.source if source else task.target):
                        meta_node = GraphContext._extract_meta_node(node)
                        if meta_node in existing_meta_nodes: continue
                        existing_meta_nodes.add(meta_node)

                        node_id = node_indexer.get_id(node)
                        node_name = "node%d" % node_id
                        task_name = "task%d" % task_id

                        if source:
                            links.append((node_name, task_name))
                        else:
                            links.append((task_name, node_name))
                return links

            def link_lines(num_invis, links):
                lines = []
                if num_invis <= 1: return lines
                for link in links:
                    invis_names = []
                    for i in range(num_invis):
                        invis_names.append("invis_point%d" % self.invis_i)
                        self.invis_i += 1
                    for invis_name in invis_names:
                        lines.append("%s[style=invis shape=point]" % invis_name)
                        
                    lines.append("%s->%s->%s[style=invis weight=100];" %
                                 (link[0], "->".join(invis_names), link[1]))
                return lines

            lines = []
            
            for meta_task in self.table:
                num_in_invis = min(self.max_num_invis,
                                   num_in_links(meta_task) / self.num_invis_per_nodes)
                num_out_invis = min(self.max_num_invis,
                                    num_out_links(meta_task) / self.num_invis_per_nodes)

                in_links = extract_meta_links(meta_task, True)
                out_links = extract_meta_links(meta_task, False)
                
                lines += link_lines(num_in_invis, in_links)
                lines += link_lines(num_out_invis, out_links)
                
            return "\n".join(lines)
                
            
    def execute(self):
        """
        See :py:func:`waflib.Context.Context.execute`.
        """
        self.restore()
        if not self.all_envs:
            self.load_envs()

        self.recurse([self.run_dir])
        self.pre_build()

        # display the time elapsed in the progress bar
        self.timer = waflib.Utils.Timer()

        tasks = [t for g in self.groups for t in g]

        node_indexer = self.NodeIndexer()
        for task in tasks:
            for node in _to_list(task.source) + _to_list(task.target):
                node_indexer.get_id(node)
        
        meta_nodes = self.MetaNodes(node_indexer.nodes)
        meta_tasks = self.MetaTasks(tasks)
        links = self._collect_links(node_indexer, tasks)

        dot = tempfile.NamedTemporaryFile()

        dot.write("digraph G {\n")
        dot.write("graph [splines=line,outputorder=edgesfirst];")
        dot.write(meta_nodes.render_graphviz(node_indexer, self) + "\n")
        dot.write(meta_tasks.render_graphviz() + "\n")
        for link in links:
            dot.write("%s->%s[color=\"#0000005f\" arrowsize=0.5 arrowhead=open]\n" %
                      (link[0], link[1]))
        dot.write(meta_tasks.render_invisibles(node_indexer))
        
        dot.write("}")

        dot.seek(0)

        graphpath = waflib.Options.options.graphpath
        ext = graphpath[graphpath.rfind(".") + 1:]

        if ext == "dot":
            subprocess.check_call(['cp', dot.name, waflib.Options.options.graphpath])
        else:
            subprocess.check_call(['dot', '-T'+ext, dot.name,
                                   '-o', waflib.Options.options.graphpath])
            
    def _collect_links(self, node_indexer, tasks):
        links = []
        for task_id, task in enumerate(tasks):
            for node_id in [node_indexer.get_id(node) for node in _to_list(task.source)]:
                links.append(("node" + str(node_id), "task" + str(task_id)))
            for node_id in [node_indexer.get_id(node) for node in _to_list(task.target)]:
                links.append(("task" + str(task_id), "node" + str(node_id)))
        return links

    def _extract_unique_nodes(self, nodes):
        abspath2nodes = {}
        for node in nodes:
            abspath2nodes[node.abspath()] = node
        return [item[1] for item in abspath2nodes.items()]

    @staticmethod
    def _extract_meta_node(node):
        if node.is_bld():
            found_meta = re.findall(r'\d+-([^/]+)', node.name)
            if found_meta:
                return found_meta[0]
            else:
                return node.name
        return node.abspath()

    @staticmethod
    def _extract_parameter_id(node):
        if node.is_bld():
            found_id = re.findall(r'(\d+)-[^/]+', node.name)
            if found_id:
                return int(found_id[0])
        return -1

        
class ExpOptionsContext(waflib.Options.OptionsContext):
    """ExperimentContext specific OptionContext.

    Please extend the `__init__` method below to add new options.

    """
    
    def __init__(self, **kw):
        super(ExpOptionsContext, self).__init__(**kw)

        default_path = 'graph.pdf'
        gr = self.add_option_group('graph options')
        gr.add_option('--graphpath', action = 'store', default = default_path,
                      help = 'path to the output of graph [default: %s]' % default_path)
        gr.add_option('--simple_param', action = 'store_true', default = False,
                      help = 'outputs parameter ids instead of specific values')
        
        
class CyclicDependencyException(Exception):
    """Exception raised when experiment graph has a cycle."""
    pass


class InvalidMafArgumentException(Exception):
    """Exception raised when arguments of ExperimentContext.__call__ is wrong.

    """
    pass


class Parameter(dict):
    """Parameter of maf task.

    This is a dict with hash(). Be careful to use it with set(); parameter has
    hash(), but is mutable.

    """
    def __hash__(self):
        # TODO(beam2d): Should we cache this value?
        return hash(frozenset(self.iteritems()))

    def conflict_with(self, parameter):
        """Checks whether the parameter conflicts with given other parameter.

        :return: True if self conflicts with parameter, i.e. contains different
            values corresponding to same key.
        :rtype: bool

        """
        common_keys = set(self) & set(parameter)
        return any(self[key] != parameter[key] for key in common_keys)

    def to_str_valued_dict(self):
        """Gets dictionary with stringized values.

        :return: A dictionary with same key and stringized values.
        :rtype: dict of str key and str value

        """
        return dict([(k, str(self[k])) for k in self])


class Rule(object):
    """A wrapper object of a rule function with associate values,
    which change is tracked on the experiment.

    :param fun: target function of the task.
    :param dependson: list of variable or function, which one wants to track.
        All these variables are later converted to string values, so if
        one wants to pass the variable of user-defined class, that class
        must provide meaningful `__str__` method.

    """

    def __init__(self, fun, dependson=[]):
        self.fun = fun
        self.dependson = dependson
        self.dependson.append(self.fun)

    def add_dependson(self, dependson):
        self.dependson += dependson

    def stred_dependson(self):
        def to_str(d):
            # Callable object is converted to its source code as str.
            if _is_callable(d):
                return inspect.getsource(d)
            else:
                return str(d)
        return map(to_str, self.dependson)


class CallObject(object):
    """Object representing one call of ``ExperimentContext.__call__()``."""

    def __init__(self, **kw):
        """Initializes a call object.

        ``kw['source']`` and ``kw['target']`` are converted into list of
        strings.

        :param **kw: Arguments of ``ExperimentContext.__call__``.

        """
        self.__dict__.update(kw)

        for key in ['source', 'target', 'features']:
            _let_element_to_be_list(self.__dict__, key)

        for key in ['for_each', 'aggregate_by']:
            if hasattr(self, key):
                _let_element_to_be_list(self.__dict__, key)

        self.__dict__['features'].append('experiment')
        if 'parameters' not in self.__dict__:
            self.parameters = [Parameter()]
            """List of parameters indicated by the taskgen call."""
        else:
            self.parameters = [Parameter(p) for p in self.parameters]

        # Some tests do not support the argument 'wscript'
        if 'wscript' in kw:
            relpath = self.wscript.parent.relpath()
            self.rel_source = [os.path.normpath(os.path.join(relpath, n)) for n in self.source]
            self.rel_target = [os.path.normpath(os.path.join(relpath, n)) for n in self.target]

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class ExperimentGraph(object):
    """Bipartite graph consisting of meta node and call object node."""

    def __init__(self):
        self._edges = collections.defaultdict(set)
        self._call_objects = []

    def add_call_object(self, call_object):
        """Adds call object node, related meta nodes and edges.

        :param call_object: Call object be added.
        :type call_object: :py:class:`CallObject`

        """
        index = len(self._call_objects)
        self._call_objects.append(call_object)

        for in_node in call_object.rel_source:
            self._edges[in_node].add(index)

        for out_node in call_object.rel_target:
            self._edges[index].add(out_node)

    def get_sorted_call_objects(self):
        """Runs topological sort on the experiment graph.

        :return: List of call objects that topologically sorted.
        :rtype: list of :py:class:`CallObject`

        """

        nodes = self._collect_independent_nodes()
        edges = copy.deepcopy(self._edges)

        reverse_edges = collections.defaultdict(set)
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
    """Consistent generator of physical nodes identifier corresponding to
    their parameters.

    Meta node has a path and its own parameters, each of which corresponds to
    one physical waf node named as 'path/N', where N is a unique name of the
    parameter. The correspondence between parameter and its name must be
    consistent over multiple execution of waf, so we serializes the table to
    hidden file.

    This class also dumps the correspondence to a human-readable text file.
    The file is tab-separated line for each correspondence: the first element
    is an identifier and the second is a JSON representation of the
    correspondent parameter.

    NOTE: On exception raised during task generation, save() must be called
    to avoid inconsistency on node names that had been generated before the
    exception was raised.

    """
    def __init__(self, path, text_path):
        """Initializes the generator.

        :param path: Path to persisitent file of the table.
        :type path: str
        :param text_path: Path to file that the table is dumped to as a human-
            readable.
        :type text_path: str

        """
        # TODO(beam2d): Isolate persistency support from resolver.

        self.path = path
        """Path to file that the table is serialized to."""

        self.text_path = text_path
        """Path to file that the table is dumped to as a human-readable text."""

        if os.path.exists(path):
            self._parameters, self._table = self._load_table(path)
        else:
            self._parameters = []
            self._table = {} # Parameter -> id

    def save(self):
        """Serializes the table to the file at self.path."""

        if len(self._table) == 0: return

        with _create_file(self.path) as f:
            # We only save a modified `self._parameters`, which is obtained by converting
            # each element of `self._parameters` into a dictionary object.
            # This is for deserializing parameter->id mappings outside without
            # maflib and waflib dependencies. Parameter class is defined in maflib,
            # so user cannot decode original objects without maflib libraries.
            dicted_params = [dict(param) for param in self._parameters]
            
            pickle.dump(dicted_params, f)

        with _create_file(self.text_path) as f:
            for id, parameter in enumerate(self._parameters):
                f.write('%s\t%s\n' % (id, parameter))

    def _load_table(self, path):
        dicted_params = []
        try:
            with open(path) as f:
                dicted_params = pickle.load(f)
        except EOFError: pass

        parameters = [Parameter(param) for param in dicted_params]
        table = {}
        for i, param in enumerate(parameters):
            if param is not None: table[param] = str(i)

        return (parameters, table)

    def get_id(self, parameter):
        """Gets the id of given parameter.

        :param parameter: Parameter object.
        :type parameter: :py:class:`Parameter`
        :return: Identifier of given parameter. The id may be generated in this
            method if necessary.
        :rtype: str

        """
        if parameter in self._table:
            return self._table[parameter]

        new_id = str(len(self._parameters))
        self._table[parameter] = new_id
        self._parameters.append(parameter)

        return new_id

    def get(self, parameter_id):
        """Gets the parameter of a given id.

        :param parameter_id: Id of the parameter
        :type parameter: int
        :return: Parameter object of a given id.
        :rtype: :py:class:`Parameter`

        """
        return self._parameters[parameter_id]


class ExperimentTask(waflib.Task.Task):
    """A task class specific for ExperimentContext.

    The purpose of this class is to bring the parameter as an attribute.
    The base class (:py:class:`waflib.Task.Task`) doesn't bring attributes
    except ``env``, but the env must be a string-valued dictionary, which is
    problematic when we want to use the parameter in an object as it is. For
    example, a float value once converted to string lose some information.

    Another motivation for this task is to control the hash value of a task:
    It is calculated based on the env, in which key is registered in ``vars``
    or ``dep_vars``. In ``__init__``, this task registers necessary keys to
    dep_vars.

    """

    shell = True
    """support pipe style rule str in default"""

    def __init__(self, env, generator):
        """Initializes the task.

        :param env: Environmental variables.
        :param generator: Generator function.

        """

        super(ExperimentTask, self).__init__(env=env, generator=generator)

        self.parameter = generator.parameter
        """Parameter whose values are not stringized."""

        self.source_parameters = generator.source_parameter
        """List of parameters each of which is the parameter of the
        corresponding input node."""

        if not hasattr(self, 'dep_vars'): self.dep_vars = []
        self.dep_vars += self.parameter.keys()
        self.dep_vars += filter(lambda k: k.startswith("dependson"), env.keys())

        self.inputs = [ExperimentNode(s) for s in self.inputs]
        self.outputs = [ExperimentNode(s) for s in self.outputs]

        
    def sig_explicit_deps(self):
        """Calculates the hash value of this task.

        Overriden from waflib.Task.Task to use ``_node_sig`` to calculate
        the hash value of source/target files.
        
        """
        
        bld = self.generator.bld
        upd = self.m.update

        # the inputs
        for x in self.inputs + self.dep_nodes:
            upd(_node_sig(x))
        
        # manual dependencies, they can slow down the builds
        if bld.deps_man:
            additional_deps = bld.deps_man
            for x in self.inputs + self.outputs:
                try:
                    d = additional_deps[id(x)]
                except KeyError:
                    continue

                for v in d:
                    if isinstance(v, bld.root.__class__):
                        try:
                            v = v.get_bld_sig()
                        except AttributeError:
                            import waflib.Errors
                            raise waflib.Errors.WafError('Missing node signature for %r (required by %r)' % (v, self))
                    elif hasattr(v, '__call__'):
                        v = v() # dependency is a function, call it
                    upd(v)
        return self.m.digest()


class ExperimentNode(object):
    """A wrapper of Node object used in ExperimentTasks for replacement of
    input/output Nodes.

    The main motivation of this class is to make it easy to write unit-tests
    for user-defined rules. In maf, a user can define his own rule by writing
    a function that receives the task object as an argument, then reads
    (writes) an input (output) Node object by accessing like
    ``task.inputs[0].read``. A user has to write a mock-object which mimics
    the behavior of Task object to test these functions, because the
    received ``task`` is generated by maf internally. This is tedious.
    ExperimentNode relieves this problem.

    This Node wrapper behaves in two different ways: At an ordinary Task
    (the usual case), this is a mere wrapper of a Node object given in the
    constructor. The commonly used methods ``read``, ``write``, and ``abspath``
    behave in the same ways as those of the ordinary Node object. At the test
    time, a user can get a *dummy* Node object using this class with no argument
    to the constructor. In that case, this class creates a temporary file and
    preserves internally. ``read`` and ``write`` methods are called to this
    temporary file, which saves some labors to define dummy Node objects for
    each rule. This class abstracts away the difference of these two cases.

    Example usages of this class at test cases are found at, for example,
    tests/test_rule.py. See also :py:func:`test.TestTask`.

    """
    def __init__(self, waflib_node=None):
        if waflib_node:
            self.node = waflib_node
            self.abspath_ = self.node.abspath()
        else:
            import tempfile
            self.tmpfile = tempfile.NamedTemporaryFile()
            self.abspath_ = self.tmpfile.name

    def read(self):
        return ''.join([line for line in open(self.abspath_)])

    def write(self, s):
        with open(self.abspath_, 'w') as o: o.write(s)

    def abspath(self):
        return self.abspath_


# Forces these commands run under ExperimentContext
waflib.Build.CleanContext.__bases__ = (ExperimentContext,)
waflib.Build.InstallContext.__bases__ = (ExperimentContext,)
waflib.Build.ListContext.__bases__ = (ExperimentContext,)
waflib.Build.StepContext.__bases__ = (ExperimentContext,)
waflib.Build.UninstallContext.__bases__ = (ExperimentContext,)


# Old command experiment
class OldExperimentContext(ExperimentContext):
    cmd = 'experiment'
    fun = 'experiment'
    variant = 'experiment'


@feature('experiment')
@before_method('process_rule')
def register_experiment_task_with_rule(self):
    """A task_gen method called before process_rule.

    WARNING: This method currently strongly connected to the internal of
    ``process_rule`` method, which is defined in :py:class:`waflib.TaskGen`, so
    may require a modification in future version of waf.

    The role of this method is to create ``self.bld.cache_rule_attr``, which
    is later used in ``process_rule``. It is a dictionary of ``(task_name, the
    rule of task)`` pair to a task class. This task class is a derived class of
    :py:class:`ExperimentTask` defined above, which override the run method of
    it with the function given by rule attribute written in wscript. This
    process is necessary because the ``process_rule`` cannot create a user-
    defined :py:class:`Task` with a user-defined rule (as in our case).

    In the current implementation of ``process_rule``, the ``cache_rule_attr``
    is used as follows;

    .. code-block:: py

        try:
            cache = self.bld.cache_rule_attr
        except AttributeError:
            cache = self.bld.cache_rule_attr = {}

        cls = None
        if getattr(self, 'cache_rule', 'True'):
            try:
                cls = cache[(name, self.rule)]
            except KeyError:
                pass
        if not cls:
            cls = Task.task_factory(name, self.rule,
            ....

    This snippet search for a task from cache_rule_attr dictionary first,
    so we set that dictionary beforehand.

    """
    self.name = str(getattr(self, 'name', None) or self.target or getattr(self.rule, '__name__', self.rule))
    params = {}
    if isinstance(self.rule, str):
        params['run_str'] = self.rule
    else:
        params['run'] = self.rule

    # define ExperimentTask with a user-defined rule (string or function)
    cls = type(waflib.Task.Task)(self.name, (ExperimentTask,), params)
    waflib.Task.classes[self.name] = cls

    self.bld.cache_rule_attr = {(self.name, self.rule):cls}


def _create_file(path):
    """Opens file in write mode. It also creates intermediate directories if
    necessary.

    """
    
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    return open(path, 'w')


def _let_element_to_be_list(d, key):
    if key not in d:
        d[key] = []
    if isinstance(d[key], str):
        d[key] = waflib.Utils.to_list(d[key])


def _to_list(objs):
    if isinstance(objs, list):
        return objs
    else:
        return [objs]


def _is_callable(o):
    return isinstance(o, types.FunctionType) or hasattr(o, '__call__')


def _node_sig(node):
    """An extended version of `Node.get_bld_sig`.

    `get_bld_sig` cannot calculate the signature (hash value unique to the file),
    so we extend here to calculate the signature of directory by reading all
    files under the directory.
    
    """
    
    try:
        return node.cache_sig
    except AttributeError:
        pass
        
    path = node.abspath()

    if not hasattr(node, 'sig') or node.sig is None or not node.is_bld() or node.ctx.bldnode is node.ctx.srcnode:
        if os.path.isdir(path):
            m = waflib.Utils.md5()
            for child in sorted(os.listdir(path)):
                m.update(_node_sig(node.make_node(child)))
            node.sig = m.digest()
        else:
            node.sig = waflib.Utils.h_file(path)
            
    node.cache_sig = ret = node.sig
    
    return ret
