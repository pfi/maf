#! /usr/bin/env python
# encoding: utf-8

from waflib import TaskGen
from maflib import Experiment
import maflib.Utils as mUtils

class SupervisedLearningTrain(Experiment.ExperimentalTask):
    def __init__(self, env, generator):
        super(SupervisedLearningTrain, self).__init__(env=env, generator=generator)
        self.parameters = env['parameters']
        # self.cmd = env['cmd']
        self.train = env['train']

    def run(self):
        super(SupervisedLearningTrain, self).run()
        parameters = self.parameters
        parameters['TRAINDATA'] = self.inputs[0].abspath()
        parameters['MODEL'] = self.outputs[0].abspath()
        
        parameters['LOGPREFIX'] = parameters['MODEL']
        return self.train(self, parameters)

        # from waflib.Utils import subst_vars
        # parameters = self.parameters
        # parameters['TRAINDATA'] = self.inputs[0].abspath()
        # parameters['MODEL'] = self.outputs[0].abspath()
        # cmd = subst_vars(self.cmd, parameters)

        # print cmd

        # from waflib.Utils import Timer
        # timer = Timer()
        # ret = self.exec_command(cmd)
        # print str(timer)

        # return ret

    def CheckInputFormat(self):
        # self.format_check(parameters['TRAINDATA'])
        return 'OK'

@TaskGen.feature('train')
def feature_train(self):
    if self.task == 'supervised-learning':
        # self.env['cmd'] = self.cmd
        self.env['train'] = self.train

        from itertools import product

        keys = sorted(self.parameters)
        param_combs = [
            dict(zip(keys, prod)) for prod in product(
                *(self.parameters[key] for key in keys))
            ]
        mUtils.save_params(self, self.model, param_combs)

        for param in param_combs:
            model = mUtils.generate_parameterized_nodename(self.model, param)
            self.env['parameters'] = param
            self.create_task('SupervisedLearningTrain',
                             src=self.bld.root.find_resource(self.traindata),
                             tgt=self.path.find_or_declare(model))
