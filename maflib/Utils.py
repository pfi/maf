#! /usr/bin/env python
# encoding: utf-8

import json

def generate_parameterized_nodename(name, param):
    '''
    model, {'C': 1, 'D': 2}
    -> (2) model/C=1_D=2
    '''
    name += '/'
    name += '_'.join([k + '=' + str(v) for k, v in param.items()])
    return name

def decode_parameterized_nodename(name):
    pairs = map(lambda x: x.split('='), name.split('_'))
    return {pair[0]: pair[1] for pair in pairs}

def save_params(taskgen, name, params):
    taskgen.path.find_or_declare(name + '/param').write(json.dumps(params))

def load_params(taskgen, name):
    params = json.loads(taskgen.path.find_resource(name + '/param').read())
    return [{
            k.encode('utf_8'): v.encode('utf_8') for (k, v) in param.iteritems()
            } for param in params]

def divide_param_combs(param_combs, varnames):
    '''
    パラメータ組合せリストparam_combsをもとに、varnamesに含まれるパラメータと
    それ以外のパラメータに分割された階層的なリストを作る。
    [({その他のパラメータ}, [varnamesパラメータ, ...]), ...] の形で返す。
    '''

    # TODO: 実装マシにする
    divided_combs = []
    for param in param_combs:
        other_param = {k: param[k] for k in param.iterkeys() if k not in varnames}
        var_param = {k: param[k] for k in param.iterkeys() if k in varnames}
        for divided in divided_combs:
            if other_param == divided[0]:
                if var_param not in divided[1]:
                    divided[1].append(var_param)
                break
        else:
            divided_combs.append((other_param, [var_param]))

    return divided_combs

def read_result(result_node):
    value = float(result_node.read())

    filename = '/'.split(result_node.abspath()).pop()
