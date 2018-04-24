import os

import json
from collections import OrderedDict
import heapq
from time import time
import subprocess as sp
from pprint import pprint
import logging
from copy import deepcopy


def read_settings(path):
    if not os.path.exists(path):
        return {}

    with open(path) as settings_file:
        text = settings_file.read()

    return json.loads(text, object_pairs_hook=OrderedDict)


def get_programs(path):
    programs = [os.path.join(path, program) for program in os.listdir(path)]
    return list(filter(os.path.isdir, programs))


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


def unwrap_commands(commands):
    if isinstance(commands, (str, int)):
        commands = [[commands], ]
    return [
        [str(cmd)] if isinstance(cmd, (str, int)) else list(map(str, cmd))
        for cmd in commands
    ]


def get_executors(settings, variables):
    executors = {}
    for name, value in settings['executors'].items():
        if isinstance(value, str):
            value = {'start': value, 'requirements': value}
        if isinstance(value, list):
            value = {'start': value, 'requirements': value[0]}

        if isinstance(value['start'], str):
            value['start'] = [value['start'], ]

        value['requirements'] = unwrap_commands(value.get('requirements', []))
        value['start'] = unwrap_commands(value.get('start', []))
        value['compile'] = unwrap_commands(value.get('compile', []))

        executors[name] = value
    return fill_variables(executors, variables)


def check_executors(executors):
    failed = set()
    for executor, settings in executors.items():
        for req in settings['requirements']:
            try:
                sp.call(req + ['--help'], stderr=sp.DEVNULL, stdout=sp.DEVNULL)
            except FileNotFoundError:
                failed.add(executor)
                logging.warning(
                    'command %r not found (%s would be skipped)',
                    req, executor)
    return failed


def run(path, settings, executors, skipped_executors):
    average_time = settings['average_time']
    time_limit = settings['time_limit']
    args = settings['args']
    if not args:
        args = [[]]

    programs = os.listdir(path)

    queue = []
    for program in programs:
        executor = program.rsplit('.', 1)[0]
        program = os.path.join(path, program)

        if (executor in skipped_executors or
                os.path.basename(program) == 'settings.json'):
            continue
        if executor not in executors:
            logging.warning('executor %s not found' % executor)
            continue

        executors[executor]['start'] = fill_variables(
            executors[executor]['start'], {'name': program})

        for arg in args:
            queue.append([0, executor, program, 0, arg])

        compiler = executors[executor].get('compile', None)
        if compiler is not None:
            for command in compiler:
                filled_command = fill_variables(command, {'name': program})
                if (not filled_command or
                        (filled_command == command and filled_command[-1] != ';')):
                    filled_command = command + [program, ]
                if filled_command[-1] == ';':
                    filled_command = filled_command[:-1]

                # print(' '.join(command))
                status = sp.call(
                    filled_command,
                    stdout=sp.DEVNULL, stderr=sp.DEVNULL)
                if status:
                    sp.call(filled_command)
                    raise ValueError(
                        "Can't execute command %r" % ' '.join(filled_command))

    heapq.heapify(queue)

    results = []

    while queue:
        cur_time, executor, program_path, iters, arg = heapq.heappop(queue)
        commands = executors[executor]['start']

        # print(' '.join(command))
        for command in commands:
            command = command + arg
            start_time = time()
            status = sp.call(command, stdout=sp.DEVNULL)
            end_time = time()
            if status:
                raise ValueError('non zero exit program code %r' %
                                 ' '.join(command))
            cur_time += end_time - start_time
        iters += 1

        if cur_time >= average_time:
            results.append((executor, cur_time / iters, arg))
            continue

        heapq.heappush(queue, [cur_time, executor, program_path, iters, arg])

    results.sort()
    return {
        'program': os.path.basename(path),
        'data': results}


def run_programs(programs=None):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    programs_dir = os.path.join(base_dir, 'programs')

    build_dir = os.path.join(base_dir, 'build')
    os.makedirs(build_dir, exist_ok=True)

    all_programs = get_programs(programs_dir)

    global_settings = read_settings(
        os.path.join(programs_dir, 'settings.json'))
    global_settings.setdefault('build_dir', build_dir)

    executors = get_executors(global_settings, {
        'build': global_settings['build_dir'],
        'name': '%(name)s',
    })
    skipped_executors = check_executors(executors)

    results = []
    for program in all_programs:
        if programs is not None and os.path.basename(program) not in programs:
            continue

        local_settings = read_settings(
            os.path.join(program, 'settings.json'))
        local_settings['args'] = unwrap_commands(
            local_settings.get('args', []))

        settings = deepcopy(global_settings)
        settings.update(local_settings)

        result = run(program, settings, executors, skipped_executors)
        if result is None:
            break
        pprint(result)
        results.append(result)
    return results


def main():
    run_programs(['sum'])


if __name__ == '__main__':
    main()
