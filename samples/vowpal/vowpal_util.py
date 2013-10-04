import subprocess

"""Utility tasks for vowpal wabbit"""

def convert_libsvm_format_to_vowpal(task):
    with open(task.outputs[0].abspath(), 'w') as o:
        for line in open(task.inputs[0].abspath()):
            first_sep = line.find(' ')
            o.write(line[:first_sep])
            o.write(' | ')
            o.write(line[first_sep+1:])

# calculate num classes from vowpal format input
def num_classes(task):
    n = max([int(line[:line.find(' ')]) for line in open(task.inputs[0].abspath())])
    task.outputs[0].write(str(n))
    
def normalize_vowpal_output(task):
    with open(task.outputs[0].abspath(), 'w') as o:
        for line in open(task.inputs[0].abspath()):
            o.write(str(int(float(line.strip()))) + '\n')

class LearningSetting(object):
    """abstract class for the setting of learning algorithm used as a Parameter

    This is an example of the use of user-defined class for parameters:
    If you want to define a class for parameter as in this example,
    please implement meaningfull __hash__(self), __eq__(self) and __repr__(self) methods 

    """
    
    def args(self):
        return []
    def __hash__(self):
        return self.__repr__().__hash__()
    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

class OnlineSetting(LearningSetting):
    def __init__(self, power_t):
        self.power_t = power_t
    def args(self):
        return ['-l', '1',
                '--initial_t', '1',
                '--power_t', str(self.power_t),
                '--sgd']
    def __repr__(self):
        return 'SGD(power_t=%.1f)' % self.power_t

class BatchSetting(LearningSetting):
    def args(self):
        return ['--bfgs']
    def __repr__(self):
        return 'LBFGS'

def train_vowpal_with_learning_setting(task):
    K = task.inputs[1].read()
    rule = ['vw', task.inputs[0].abspath(),
            '--loss_function', 'hinge',
            '-c',
            '--passes', task.env['pass'],
            '-f', task.outputs[0].abspath(),
            '--oaa', K]
    
    rule += task.parameter['learn'].args()
    subprocess.check_call(rule)
    return 0
