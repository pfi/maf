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

from maflib.core import *
import tempfile
import os
import shutil
import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest
import shutil

from waflib.Node import Node

class TestParameter(unittest.TestCase):
    def test_empty_parameter_does_not_conflict(self):
        p = Parameter()
        q = Parameter()
        self.assertFalse(p.conflict_with(q))

    def test_empty_parameter_to_str(self):
        p = Parameter()
        p_str = p.to_str_valued_dict()
        self.assertDictEqual({}, p_str)

    def test_conflicted_parameters(self):
        p = Parameter(a=1, b=2, c=3)
        q = Parameter(a=2, b=2, d=4)
        self.assertTrue(p.conflict_with(q))

    def test_not_conflicted_parameters(self):
        p = Parameter(a=1, b=2, c=3)
        q = Parameter(a=1, b=2, d=4)
        self.assertFalse(p.conflict_with(q))

    def test_dict_with_parameter_keys(self):
        d = {}
        d[Parameter(a=1)] = 1
        d[Parameter(a=1, b=2)] = 2
        d[Parameter(a=2)] = 3

        self.assertEqual(1, d[Parameter(a=1)])
        self.assertEqual(2, d[Parameter(a=1, b=2)])
        self.assertEqual(3, d[Parameter(a=2)])

    def test_dict_with_parameter_keys_modified(self):
        d = {}
        d[Parameter(a=1, b=2)] = 1

        p = Parameter()
        p['a'] = 1
        p['c'] = 3
        p['b'] = 2
        del p['c']

        self.assertEqual(1, d[p])

    def test_dict_with_parameter_keys_not_exist(self):
        d = {}
        d[Parameter(a=1)] = 1
        d[Parameter(a=1, b=2)] = 2

        self.assertFalse(Parameter(a=2) in d)
        self.assertFalse(Parameter(a=1, b=2, c=3) in d)


class Setting(object):
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c
    def __eq__(self, other):
        return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)
    def __ne__(self, other): return not self.__eq__(other)

    
class TestParameterIdGenerator(unittest.TestCase):
    def test_decode_pickled_parameter_with_object(self):
        # TODO(noji): change to use tempfile for generating pickle_path after revise_create_file is merged
        # pickle_path = tempfile.NamedTemporaryFile()
        # text_path = tempfile.NamedTemporaryFile()
        # pickle_path.close()
        # text_path.close()
        # pickle_path = pickle_path.name
        # text_path = text_path.name

        def clean_environment():
            if os.path.exists(".maf_tmp_dir"): shutil.rmtree(".maf_tmp_dir")

        clean_environment()
        try:
            pickle_path = ".maf_tmp_dir/tmp_parameters.pickle"
            text_path = ".maf_tmp_dir/tmp_parameters.txt"

            id_generator = ParameterIdGenerator(pickle_path, text_path)

            id_generator.get_id(Parameter({"setting": Setting(0,1,2)}))
            id_generator.save()
        
            table = pickle.load(open(pickle_path))
        
            self.assertEqual(1, len(table))
            self.assertEqual({"setting":Setting(0,1,2)}, table[0])
        finally:
            clean_environment()

            
class TestCallObject(unittest.TestCase):
    def test_listize_source(self):
        self._test_listize('source')

    def test_listize_target(self):
        self._test_listize('target')

    def test_listize_features(self):
        self._test_listize('features')

    def test_listize_for_each(self):
        self._test_listize('for_each')

    def test_listize_aggregate_by(self):
        self._test_listize('aggregate_by')

    def test_default_parameters(self):
        co = CallObject()
        self.assertListEqual([Parameter()], co.parameters)

    def test_features_experiment(self):
        co = CallObject()
        self.assertIn('experiment', co.features)

    def test_equality(self):
        co1 = CallObject(source='a b c', target='d e', features='x', for_each='p q')
        co2 = CallObject(source='a b c', target='d e', features='x', for_each='p q')
        self.assertEqual(co1, co2)

    def _test_listize(self, key):
        queries = [('a ab c', ['a', 'ab', 'c'])]
        for query in queries:
            co = CallObject(**{ key: query[0] })
            self.assertTrue(isinstance(getattr(co, key), list))
            for q in query[1]:
                self.assertIn(q, getattr(co, key))


class TestExperimentGraph(unittest.TestCase):
    def test_empty_graph(self):
        g = ExperimentGraph()
        cos = g.get_sorted_call_objects()
        self.assertEqual([], cos)

    def test_path_graph(self):
        self._test_graph(
            [('c', 'd'), ('a', 'b'), ('d', 'e'), ('b', 'c')],
            [(1, 3), (3, 0), (0, 2)])

    def test_tree_graph(self):
        self._test_graph(
            [('b', 'c'), ('a', 'b'), ('b', 'd')], [(1, 0), (1, 2)])

    def test_tree_graph_2(self):
        self._test_graph(
            [('b', 'c'), ('a', 'd'), ('a', 'b')], [(2, 0)])

    def test_tree_graph_3(self):
        self._test_graph(
            [('b', 'c'), ('d', 'h'), ('c', 'f'), ('a', 'b'), ('b', 'e'),
             ('d', 'g'), ('b', 'd')],
            [(3, 0), (0, 2), (3, 4), (3, 6), (6, 1), (6, 5)])

    def test_reverse_tree_graph(self):
        self._test_graph(
            [('a', 'c'), ('c', 'd'), ('b', 'c')], [(0, 1), (2, 1)])

    def test_reverse_tree_graph_2(self):
        self._test_graph(
            [('b', 'd'), ('c', 'd'), ('a', 'b')], [(2, 0)])

    def test_reverse_tree_graph_3(self):
        self._test_graph(
            [('a', 'd'), ('b', 'd'), ('d', 'f'), ('e', 'f'), ('c', 'd')],
            [(0, 2), (1, 2), (4, 2)])

    def test_diamond_graph(self):
        self._test_graph(
            [('a', 'b'), ('c', 'd'), ('b', 'd'), ('a', 'c')],
            [(0, 2), (3, 1)])

    def test_acyclic_graph(self):
        self._test_graph(
            [('b', 'f'), ('d', 'f'), ('a', 'c'), ('a', 'd'), ('a', 'e'), ('c', 'f')],
            [(2, 5), (3, 1)])

    def test_hyper_reverse_tree_graph(self):
        self._test_graph(
            [('d', 'e'), ('a b', 'd'), ('c', 'd')], [(1, 0), (2, 0)])

    def test_hyper_tree_graph(self):
        self._test_graph(
            [('b', 'c d'), ('a', 'b'), ('b', 'e')], [(1, 0), (1, 2)])

    def test_hyper_acyclic_graph(self):
        self._test_graph(
            [('d', 'e f'), ('c', 'd'), ('a b', 'd'), ('d', 'g')],
            [(2, 0), (2, 3), (1, 0), (1, 3)])

    def test_cycle(self):
        with self.assertRaises(CyclicDependencyException):
            self._test_graph([('a', 'b'), ('c', 'a'), ('b', 'c')], [])

    def test_cyclic_graph(self):
        with self.assertRaises(CyclicDependencyException):
            self._test_graph(
                [('c', 'd'), ('a', 'c'), ('b', 'c'), ('c', 'e'), ('d', 'b'),
                 ('b', 'e')],
                [])

    def test_subdir(self):
        self._test_graph(
            [('sub/s', 'u'), ('../t', 's'), ('a', 't')],
            [(1, 0), (2, 1)],
            [('.', 'wscript'), ('sub', 'sub/wscript'), ('.', 'wscript')])

    def _test_graph(self, edges, order, wscript_at=None):
        # dummy node
        class NodeLike:
            def __init__(self, relpath, parent):
                self.rp = relpath
                self.parent = parent

            def relpath(self):
                return self.rp

        root = NodeLike('.', None)
        if wscript_at is None:
            cos = [CallObject(source=src, target=tgt, wscript=NodeLike('', root)) for src, tgt in edges]
        else:
            cos = [CallObject(source=src, target=tgt, wscript=NodeLike('', NodeLike(rp, w))) for (src, tgt), (rp, w) in zip(edges, wscript_at)]

        g = ExperimentGraph()
        for co in cos:
            g.add_call_object(co)

        sorted_cos = g.get_sorted_call_objects()
        for former, latter in order:
            former_at = None
            latter_at = None
            for i, co in enumerate(sorted_cos):
                if co == cos[former]:
                    former_at = i
                elif co == cos[latter]:
                    latter_at = i

            self.assertLess(former_at, latter_at)

class TestUtility(unittest.TestCase):    
    def test_create_file_relative_path(self):
        relpath = ".maflib_test_utility_tmp_dir_rel/tmpfile"
        self._write_and_read(relpath)
        shutil.rmtree(".maflib_test_utility_tmp_dir_rel")
        
    def test_create_file_existing_path(self):
        tmp_path = tempfile.NamedTemporaryFile()
        tmp_path.close()
        self._write_and_read(tmp_path.name)
        
    def test_create_file_absolute_path(self):
        abspath = os.path.abspath(".maflib_test_utility_tmp_dir_abs/tmpfile")
        self._write_and_read(abspath)
        shutil.rmtree(".maflib_test_utility_tmp_dir_abs")

    def _write_and_read(self, path):
        import maflib.core
        with maflib.core._create_file(path) as f: f.write("aaa")
        self.assertEqual(self._read(path), "aaa")
        
    def _read(self, path): return "".join([line for line in open(path)])
