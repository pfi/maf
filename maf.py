#! /usr/bin/env python
# encoding: utf-8

from waflib.Build import BuildContext
from waflib import Utils
import json

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
                ret = self.run_command(task, d, c)
                return ret
        else:
            def callback(task, d, output_fn):
                from tempfile import NamedTemporaryFile

                cmd_out = NamedTemporaryFile()
                cmd = command.replace('$@', cmd_out.name)
                cmd = Utils.subst_vars(cmd, d)

                # success = task.exec_command(cmd)
                success = self.run_command(task, d, cmd)
                if success != 0:
                    return success

                accuracy = postprocess(cmd_out.name)
                Utils.writef(output_fn, str(accuracy))

                return 0

        return callback
    def run_command(self, task, d, command):
        import waflib.Context, os
        bld = task.generator.bld

        log = {}
        log["command"] = command
        params = d.copy()
        params.pop('LOGPREFIX', '')
        log["params"] = params
        
        timer = Utils.Timer()
        try:
            out, err = bld.cmd_and_log(
                command, output = waflib.Context.BOTH, quiet=waflib.Context.BOTH)
        except Exception as e:
            print(e.stdout, e.stderr)
            return 1
        log["time"] = str(timer)

        if 'LOGPREFIX' in d:
            prefix = d['LOGPREFIX']
            Utils.check_dir(prefix[:prefix.rfind('/')])
            if out:
                Utils.writef(prefix + '.out', out)
            if err:
                Utils.writef(prefix + '.err', err)
            Utils.writef(prefix + '.log', json.dumps(log))
        else:
            if out:
                bld.to_log('out: %s' % out)
            if err:
                bld.to_log('err: %s' % err)
        return 0
