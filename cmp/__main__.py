import os

import json
from collections import OrderedDict
import heapq
from time import time
import subprocess as sp
from pprint import pprint


def read_settings(path):
    with open(path) as settings_file:
        text = settings_file.read()

    return json.loads(text, object_pairs_hook=OrderedDict)


def get_programms(path):
    programms = [os.path.join(path, programm) for programm in os.listdir(path)]
    return list(filter(os.path.isdir, programms))


def fill_variables(obj, variables):
    if isinstance(obj, str):
        return obj % variables
    elif isinstance(obj, (list, tuple,)):
        return type(obj)([fill_variables(_, variables) for _ in obj])
    elif isinstance(obj, dict):
        return {
            key: fill_variables(value, variables)
            for key, value in obj.items()}
    else:
        raise ValueError('cant fill variables (unknown object type)')


def get_executors(settings, variables):
    executors = {}
    for name, value in settings['executors'].items():
        if isinstance(value, (str, list,)):
            value = {'start': value}

        if isinstance(value['start'], str):
            value['start'] = [value['start'], ]

        executors[name] = value
    return fill_variables(executors, variables)


def run(path, settings):
    average_time = settings['average_time']
    time_limit = settings['time_limit']
    executors = get_executors(settings, {
        'build': settings['build_dir'],
    })

    programms = os.listdir(path)

    queue = []
    for program in programms:
        executor = program.rsplit('.', 1)[0]
        program = os.path.join(path, program)
        queue.append([0, executor, program, 0])

        compiler = executors[executor].get('compile', None)
        if compiler is not None:
            command = compiler + [program, ]
            # print(' '.join(command))
            sp.call(command, stdout=sp.DEVNULL)

    heapq.heapify(queue)

    results = []

    while queue:
        cur_time, executor, program_path, iters = heapq.heappop(queue)
        command = executors[executor]['start'] + [program_path]

        # print(' '.join(command))
        start_time = time()
        sp.call(command, stdout=sp.DEVNULL)
        end_time = time()
        cur_time += end_time - start_time
        iters += 1

        if cur_time >= average_time:
            results.append((cur_time / iters, executor))
            continue

        heapq.heappush(queue, [cur_time, executor, program_path, iters])

    results.sort()
    return {
        'program': os.path.basename(path),
        'results': results}


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    programms_dir = os.path.join(base_dir, 'programms')

    build_dir = os.path.join(base_dir, 'build')
    os.makedirs(build_dir, exist_ok=True)

    programms = get_programms(programms_dir)

    settings = read_settings(os.path.join(programms_dir, 'settings.json'))
    settings.setdefault('build_dir', build_dir)

    for programm in programms:
        pprint(run(programm, settings))


if __name__ == '__main__':
    main()
