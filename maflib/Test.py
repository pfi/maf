#! /usr/bin/env python
# encoding: utf-8

from waflib import TaskGen
from waflib import Utils
from maflib import Experiment
import maflib.Utils as mUtils
import json

class SupervisedLearningTest(Experiment.ExperimentalTask):
    def __init__(self, env, generator):
        super(SupervisedLearningTest, self).__init__(env=env, generator=generator)
        # self.cmd = self.env['cmd']
        # self.testfun = self.env['testfun']
        self.test = env['test']
        self.parameters = getattr(env, 'parameters', {})
    
    def run(self):
        parameters = self.parameters
        parameters['TESTDATA'] = self.inputs[0].physicalpath()
        parameters['MODEL'] = self.inputs[1].physicalpath()
        
        log = {}
        log["params"] = parameters
        timer = Utils.Timer()
        ret = self.test(self, parameters, self.outputs[0].abspath())
        log["time"] = str(timer)
        log["command"] = ret[1]

        ret = ret[0]
        self.outputs[1].write(json.dumps(log))
        return ret

@TaskGen.feature('test')
@TaskGen.after_method('feature_train')
def feature_test(self):
    if self.task == 'supervised-learning':
        # self.env['testfun'] = self.testfun
        # self.env['cmd'] = self.cmd
        self.env['test'] = self.test

        param_combs = mUtils.load_params(self, self.model)
        self.result_log = self.result + '/log'
        print 'save param:', self.result
        mUtils.save_params(self, self.result, param_combs)
        mUtils.save_params(self, self.result_log, param_combs)

        for param in param_combs:
            each_model = mUtils.generate_parameterized_nodename(self.model, param)
            result = mUtils.generate_parameterized_nodename(self.result, param)
            result_log = mUtils.generate_parameterized_nodename(self.result_log, param)
            self.env['parameters'] = param
            self.create_task('SupervisedLearningTest',
                             src=[self.bld.root.find_resource(self.testdata),
                                  self.path.find_resource(each_model)
                                  ],
                             tgt=[self.path.find_or_declare(result),
                                  self.path.find_or_declare(result_log)])
