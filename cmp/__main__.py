import os

import json
from collections import OrderedDict
import heapq
from time import time
import subprocess as sp
from pprint import pprint
import logging


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


def unwrap_commands(commands):
    if isinstance(commands, str):
        commands = [[commands], ]
    return [
        [cmd] if isinstance(cmd, str) else list(cmd)
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

    programms = os.listdir(path)

    queue = []
    for program in programms:
        executor = program.rsplit('.', 1)[0]
        program = os.path.join(path, program)

        if executor in skipped_executors:
            continue
        if executor not in executors:
            logging.warning('executor %s not found' % executor)
            continue

        queue.append([0, executor, program, 0])

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
        cur_time, executor, program_path, iters = heapq.heappop(queue)
        commands = executors[executor]['start']



        # print(' '.join(command))
        for command in commands:
            command = command + [program_path]
            start_time = time()
            sp.call(command, stdout=sp.DEVNULL)
            end_time = time()
            cur_time += end_time - start_time
        iters += 1

        if cur_time >= average_time:
            results.append((executor, cur_time / iters))
            continue

        heapq.heappush(queue, [cur_time, executor, program_path, iters])

    results.sort()
    return {
        'program': os.path.basename(path),
        'data': results}


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    programms_dir = os.path.join(base_dir, 'programms')

    build_dir = os.path.join(base_dir, 'build')
    os.makedirs(build_dir, exist_ok=True)

    programms = get_programms(programms_dir)

    settings = read_settings(os.path.join(programms_dir, 'settings.json'))
    settings.setdefault('build_dir', build_dir)

    executors = get_executors(settings, {
        'build': settings['build_dir'],
        'name': '%(name)s',
    })
    skipped_executors = check_executors(executors)

    results = []
    for programm in programms:
        result = run(programm, settings, executors, skipped_executors)
        if result is None:
            break
        pprint(result)
        results.append(result)
    return results


if __name__ == '__main__':
    main()
