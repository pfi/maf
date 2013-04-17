#! /usr/bin/env python
# encoding: utf-8

# 共通で使うクラスなど？

import json
import waflib.Node
from waflib.Task import Task
from waflib import Utils
from waflib import Context
from waflib.Build import BuildContext
import maflib.Utils as mUtils

# TODO: パラメタ化が中途半端
class ExperimentNode(waflib.Node.Node):
    def __setstate__(self, data):
        super(ExperimentNode, self).__setstate__(data)
        if data[4] is not None: # NOTE: 親のNodeが、始めの4つを埋めることを仮定
            self.physical = data[4]
            
    def __getstate__(self):
        return super(ExperimentNode, self).__getstate__() + (getattr(self, 'physical', None),)
        
    def find_or_declare_paramed_node(self, param, model, physical_model = None):
        paramed_model = mUtils.generate_parameterized_nodename(model, param)
        node = super(ExperimentNode, self).find_or_declare(paramed_model)
        if physical_model is not None:
            node.physical = mUtils.generate_parameterized_nodename(physical_model, param)
        return node

    def physicalpath(self):
        if self.hasphysical():
            return self.physical
        else:
            return self.abspath()
        
    def hasphysical(self):
        return hasattr(self, 'physical')
    
    def update(self):
        if self.hasphysical():
            import datetime
            d = datetime.datetime.today()
            log = "%s:%s:%s:%s:%s:%s:%s" % (d.year, d.month, d.day, d.hour, d.minute, d.second, d.microsecond) + "\n" + self.physical
            self.write(log)

class ExperimentalTask(Task):
    def __init__(self, *k, **kw):
        super(ExperimentalTask, self).__init__(*k, **kw)
        self.log = {}
        self.log_node = None

    def get_log_node(self):
        # please override
        # return self.outputs[1]
        return None
    
    def run(self):
        timer = Utils.Timer()
        ret = self.run_impl()
        self.log['time'] = str(timer)

        log_node = self.get_log_node()
        if log_node:
            log_node.write(json.dumps(self.log))
            
        for output in self.outputs:
            if output.hasphysical():
                output.update()

        return ret

