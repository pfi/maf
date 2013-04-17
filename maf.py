#! /usr/bin/env python
# encoding: utf-8

def find_maflib():
    return './maflib'

def options(opt):
    pass

def configure(conf):
    mafdir = find_maflib()
    conf.load('Experiment', tooldir=mafdir)
    conf.load('Train', tooldir=mafdir)
    conf.load('Test', tooldir=mafdir)
    conf.load('CrossValidation', tooldir=mafdir)
    conf.load('Draw', tooldir=mafdir)

import maflib.Experiment
from waflib.Build import BuildContext
from waflib import Context
from waflib import Utils
from maflib.CrossValidation import generate_cv_taskgen

class ExperimentContext(BuildContext):
    cmd = 'experiment'
    fun = 'experiment'
    variant = 'experiment'

    def __init__(self, **kw):
        super(ExperimentContext, self).__init__(**kw)
        try:
            rd = kw['run_dir']
        except KeyError:
            global run_dir
            rd = Context.run_dir
        # binds the context to the nodes in use to avoid a context singleton

        class node_class(maflib.Experiment.ExperimentNode):
            pass
        self.node_class = node_class
        self.node_class.__module__ = "waflib.Node"
        self.node_class.__name__ = "Nod3"
        self.node_class.ctx = self

        self.root = self.node_class('', None)
        self.cur_script = None
        self.path = self.root.find_dir(rd)

    def cv(self, **kw):
        generate_cv_taskgen(self, **kw)

    def sh(self, command, postprocess=Utils.readf):
        import waflib.Context
        if command.find('$@') == -1:
            def callback(task, d):
                c = Utils.subst_vars(command, d)
                
                try:
                    self.cmd_and_log(c, quiet=waflib.Context.BOTH)
                except Exception as e:
                    print(e.stdout, e.stderr)
                    return 1, c
                # ret = self.run_command(task, d, c)
                return 0, c
        else:
            def callback(task, d, output_fn):
                from tempfile import NamedTemporaryFile

                cmd_out = NamedTemporaryFile()
                cmd = command.replace('$@', cmd_out.name)
                cmd = Utils.subst_vars(cmd, d)

                try:
                    self.cmd_and_log(cmd, quiet=waflib.Context.BOTH)
                except Exception as e:
                    print(e.stdout, e.stderr)
                    return 1, cmd

                accuracy = postprocess(cmd_out.name)
                Utils.writef(output_fn, str(accuracy))

                return 0, cmd

        return callback

    def dfs(self, zookeepers, jubaserver_map, task):
        def callback():
            pass
