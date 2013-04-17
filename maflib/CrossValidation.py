#! /usr/bin/env python
# encoding: utf-8

from waflib import TaskGen
from maflib import Experiment, Train, Test
import maflib.Utils as mUtils
import json

def create_cv_train_test(divided_data, prefix, k):
    train_path = prefix + str(k) + '.train'
    test_path = prefix + str(k) + '.test'

    train_idxs = [i for i in range(len(divided_data)) if i != k]

    with open(train_path, 'w') as train_f:
        for i in train_idxs:
            data = divided_data[i]
            for j, line in enumerate(data):
                train_f.write(line)
                if j != len(data)-1 or i != train_idxs[-1]: train_f.write('\n')

    with open(test_path, 'w') as test_f:
        data = divided_data[k]
        for line in data[:-1]:
                test_f.write(line + '\n')
        test_f.write(data[-1])
    return train_path, test_path

class CrossValidationCalcAverage(Experiment.ExperimentalTask):
    def __init__(self, env, generator):
        super(CrossValidationCalcAverage, self).__init__(env=env, generator=generator)
        self.score = env['score']

    def run(self):
        for param, result_nodes in self.env['param2results'].items():
            ave = 0
            for node in result_nodes:
                j = json.loads(node.read())
                ave += j[self.score]
            ave /= len(result_nodes)

            with open(self.env['param2target_nodes'][param].abspath(), 'w') as output:
                output.write(str(ave))

@TaskGen.feature('calc_average')
@TaskGen.after_method('feature_test')
def feature_calc_average(self):
    model = self.model + "/0"
    param_combs = mUtils.load_params(self, model)
    param2results = {}
    param2target_nodes = {}
    all_result_nodes = []
    ave_dir = self.model + '/ave-result'
    mUtils.save_params(self, ave_dir, param_combs)
    
    for param in param_combs:
        target_name = mUtils.generate_parameterized_nodename(ave_dir, param)
        target_node = self.path.find_or_declare(target_name)
        param_j = json.dumps(param)
        param2results[param_j] = []
        param2target_nodes[param_j] = target_node
        for i in range(self.num_validation):
            result_name = mUtils.generate_parameterized_nodename(
                self.model + '/' + str(i) + '-result', param)
            result_node = self.path.find_resource(result_name)
            param2results[param_j].append(result_node)
            all_result_nodes.append(result_node)
    self.env['param2results'] = param2results
    self.env['param2target_nodes'] = param2target_nodes
    self.env['score'] = self.score
    self.create_task('CrossValidationCalcAverage',
                     src = all_result_nodes)

def generate_cv_taskgen(exp, **kw):
    class LazyEncoder(json.JSONEncoder):
        def default(self, o):
            import types
            try:
                return json.JSONEncoder.default(self, o)
            except TypeError:
                return None
                # return json.JSONEncoder.default(self, 'hoge')

    encoded_self = str(json.dumps(kw, skipkeys=True, cls=LazyEncoder).encode('hex'))
    l = len(encoded_self) / 20
    tmp_prefix = '/tmp/' + "".join([encoded_self[i] for i in range(0, len(encoded_self), l)])

    divided_data = kw['divide_fun'](
        exp.root.find_resource(kw['data']).read().split('\n'), kw['num_validation'])
    assert(len(divided_data) == kw['num_validation'])
    model_prefix = kw['model']
    for k in range(kw['num_validation']):
        train_path, test_path = create_cv_train_test(divided_data, tmp_prefix, k)
        
        model = model_prefix + '/' + str(k)
        exp(features = 'train',
            task = kw['task'],
            traindata = train_path,
            model = model,
            parameters = kw['parameters'],
            train = kw['train'])
        exp(features = 'test',
            task = kw['task'],
            testdata = test_path,
            result = model + "-result",
            model = model,
            test = kw['test'])
    exp(features = 'calc_average',
        model = kw['model'],
        num_validation = kw['num_validation'],
        score = kw['score'])
