#! /usr/bin/env python
# encoding: utf-8

from waflib import TaskGen
from maflib import Experiment, Train, Test
import maflib.Utils as mUtils
import json

def create_cv_train_test(divided_data, k):
    import string, random
    alphabets = string.digits + string.letters
    
    prefix = ''.join(random.choice(alphabets) for i in range(5))
    train_path = '/tmp/maf' + prefix + '.train'
    test_path = '/tmp/maf' + prefix + '.test'
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
    def run(self):
        for param, result_nodes in self.env['param2results'].items():
            ave = sum([float(node.read()) for node in result_nodes]) / len(result_nodes)
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
    for param in param_combs:
        target_name = mUtils.generate_parameterized_nodename(self.model + '/ave-result', param)
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
    self.create_task('CrossValidationCalcAverage',
                     src = all_result_nodes)

@TaskGen.feature('cv')
def feature_cross_varidation(self):
    divided_data = self.divide_fun(
        self.bld.root.find_resource(self.data).read().split('\n'), self.num_validation)
    assert(len(divided_data) == self.num_validation)
    model_prefix = self.model
    for k in range(self.num_validation):
        train_path, test_path = create_cv_train_test(divided_data, k)
        
        model = model_prefix + '/' + str(k)
        self.bld(features = 'train',
                 task = self.task,
                 traindata = train_path,
                 model = model,
                 parameters = self.parameters,
                 train = self.train)
        self.bld(features = 'test',
                 task = self.task,
                 testdata = test_path,
                 result = model + "-result",
                 model = model,
                 test = self.test)
    self.bld(features = 'calc_average',
             model = self.model,
             num_validation = self.num_validation)
