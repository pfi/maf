#! /usr/bin/env python
# encoding: utf-8

from waflib import TaskGen
from waflib import Utils
from maflib import Experiment
import maflib.Utils as mUtils
import json

class SupervisedLearningTrain(Experiment.ExperimentalTask):
    def __init__(self, env, generator):
        super(SupervisedLearningTrain, self).__init__(env=env, generator=generator)
        self.parameters = env['parameters']
        # self.cmd = env['cmd']
        self.train = env['train']

    def get_log_node(self):
        return self.outputs[1]

    def run_impl(self):
        parameters = self.parameters
        if self.inputs:
            parameters['TRAINDATA'] = self.inputs[0].physicalpath()

        # parameters['TRAINDATA'] = self.inputs[0].physicalpath()
        parameters['MODEL'] = self.outputs[0].physicalpath()

        self.log["params"] = parameters
        ret, cmd = self.train(self, parameters)
        
        self.log["command"] = cmd

        return ret

    def CheckInputFormat(self):
        # TODO(beam2d): Implement it.
        return 'OK'

# physical_path が指定されていた場合、そのパス + model_name が、${MODEL}として渡される。
# その場合、build/experiment/model/... 以下に、モデルファイルが置かれる

@TaskGen.feature('train')
def feature_train(self):
    if self.task == 'supervised-learning':
        self.env['train'] = self.train

        model_log = self.model + '/log'
        mUtils.save_params(self, self.model, self.parameters)
        mUtils.save_params(self, model_log, self.parameters)
        physical_model = getattr(self, 'physical_model', None)

        if hasattr(self, 'traindata'):
            src = self.bld.root.find_resource(self.traindata)
        else:
            src = None
        for param in self.parameters:
            self.env['parameters'] = param
            self.create_task(
                'SupervisedLearningTrain',
                src=src,
                tgt=[self.path.find_or_declare_paramed_node(param, self.model, physical_model),
                     self.path.find_or_declare_paramed_node(param, model_log)])
            # model = mUtils.generate_parameterized_nodename(self.model, param)
            # model_log = mUtils.generate_parameterized_nodename(self.model_log, param)
            
            # self.env['parameters'] = param
            # self.create_task('SupervisedLearningTrain',
            #                  src=self.bld.root.find_resource(self.traindata),
            #                  tgt=[self.path.find_or_declare(model, physical_model),
            #                       self.path.find_or_declare(model_log, physical_model)])
