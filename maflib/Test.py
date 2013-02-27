#! /usr/bin/env python
# encoding: utf-8

from waflib import TaskGen
from maflib import Experiment
import maflib.Utils as mUtils

class SupervisedLearningTest(Experiment.ExperimentalTask):
    def __init__(self, env, generator):
        super(SupervisedLearningTest, self).__init__(env=env, generator=generator)
        # self.cmd = self.env['cmd']
        # self.testfun = self.env['testfun']
        self.test = env['test']
        self.parameters = getattr(env, 'parameters', {})

    def run(self):
        parameters = self.parameters
        parameters['TESTDATA'] = self.inputs[0].abspath()
        parameters['MODEL'] = self.inputs[1].abspath()
        parameters['LOGPREFIX'] = self.outputs[0].abspath()
        return self.test(self, parameters, self.outputs[0].abspath())

        # from waflib.Utils import subst_vars
        # from tempfile import NamedTemporaryFile

        # cmd_out = NamedTemporaryFile()

        # cmd = subst_vars(self.cmd, {
        #         'TESTDATA': self.inputs[0].abspath(),
        #         'MODEL': self.inputs[1].abspath(),
        #         'RESULT': cmd_out.name
        #         })

        # success = self.exec_command(cmd)
        # if success != 0:
        #     return success

        # accuracy = self.testfun(cmd_out.name)

        # with open(self.outputs[0].abspath(), 'w') as output:
        #     output.write(str(accuracy))

        # return 0

@TaskGen.feature('test')
@TaskGen.after_method('feature_train')
def feature_test(self):
    if self.task == 'supervised-learning':
        # self.env['testfun'] = self.testfun
        # self.env['cmd'] = self.cmd
        self.env['test'] = self.test

        param_combs = mUtils.load_params(self, self.model)
        mUtils.save_params(self, self.result, param_combs)

        for param in param_combs:
            each_model = mUtils.generate_parameterized_nodename(self.model, param)
            result = mUtils.generate_parameterized_nodename(self.result, param)
            self.env['parameters'] = param
            self.create_task('SupervisedLearningTest',
                             src=[self.bld.root.find_resource(self.testdata),
                                  self.path.find_resource(each_model)
                                  ],
                             tgt=self.path.find_or_declare(result)
                             )
