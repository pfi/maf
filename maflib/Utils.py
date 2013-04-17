#! /usr/bin/env python
# encoding: utf-8

import json

def generate_parameterized_nodename(name, param):
    '''
    traindataをパラメータに組み込む場合、パスを指定するので、ファイル名だけを取り出す
    '''
    def simplify(v):
        slash = v.find('/')
        if slash != -1 and slash != len(v) - 1:
            return v[v.rfind('/') + 1:]
        else:
            return v
    '''
    model, {'C': 1, 'D': 2}
    -> (2) model/C=1_D=2
    '''
    name += '/'
    name += '_'.join([k + '=' + simplify(str(v)) for k, v in param.items()])
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

def parse_time_string(s):
    # %dd%dh%dm%.3fs
    pos_d = s.find('d')
    pos_h = s.find('h')
    pos_m = s.find('m')

    d, h, m = 0, 0, 0

    pos_cur = 0
    if pos_d > 0:
        d = int(s[pos_cur:pos_d])
        pos_cur = pos_d + 1
    if pos_h > 0:
        h = int(s[pos_cur:pos_h])
        pos_cur = pos_h + 1
    if pos_m > 0:
        m = int(s[pos_cur:pos_m])
        pos_cur = pos_m + 1
    s = float(s[pos_cur:-1])

    return (d, h, m, s)

def convert_to_days(s):
    d, h, m, s = parse_time_string(s)
    return d + (h + (m + s / 60.0) / 60.0) / 24.0

def convert_to_hours(s):
    d, h, m, s = parse_time_string(s)
    return d * 24 + h + (m + s / 60.0) / 60.0

def convert_to_minutes(s):
    d, h, m, s = parse_time_string(s)
    return (d * 24 + h) * 60 + m + s / 60.0

def convert_to_seconds(s):
    d, h, m, s = parse_time_string(s)
    return ((d * 24 + h) * 60 + m) * 60 + s
