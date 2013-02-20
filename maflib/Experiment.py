#! /usr/bin/env python
# encoding: utf-8

# 共通で使うクラスなど？

from waflib.Task import Task

class ExperimentalTask(Task):
    def run(self):
        Timer timer
        run_body(self)
        
        # hakaru
        # logging

    def run_body(self):
        pass

        if self.CheckInputFormat() != 'OK':
            from waflib.Errors import BuildError
            raise BuildError([self])
        
        
