#! /usr/bin/env python
# encoding: utf-8

from waflib.Build import BuildContext
from waflib import Utils

def find_maflib():
    return './maflib'

def options(opt):
    pass

def configure(conf):
    mafdir = find_maflib()
    conf.load('Train', tooldir=mafdir)
    conf.load('Test', tooldir=mafdir)
    conf.load('CrossValidation', tooldir=mafdir)
    conf.load('Draw', tooldir=mafdir)

class ExperimentContext(BuildContext):
    cmd = 'experiment'
    fun = 'experiment'
    variant = 'experiment'
    
    def sh(self, command, postprocess=Utils.readf):
        if command.find('$@') == -1:
            def callback(task, d):
                c = Utils.subst_vars(command, d)
                timer = Utils.Timer()
                ret = task.exec_command(c)
                print str(timer)
                return ret
        else:
            def callback(task, d, output_fn):
                from tempfile import NamedTemporaryFile

                cmd_out = NamedTemporaryFile()
                cmd = command.replace('$@', cmd_out.name)
                cmd = Utils.subst_vars(cmd, d)

                success = task.exec_command(cmd)
                if success != 0:
                    return success

                accuracy = postprocess(cmd_out.name)
                Utils.writef(output_fn, str(accuracy))

                return 0

        return callback
