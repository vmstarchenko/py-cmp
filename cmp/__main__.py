import os

import json
from collections import OrderedDict
import heapq
from time import time
import subprocess as sp
from pprint import pprint
import logging
from copy import deepcopy
from functools import total_ordering
from itertools import groupby
from string import Template


class Command(list):
    def __init__(self, command, variables=None):
        super().__init__(map(str, command))
        variables = variables or {}
        args = variables.pop('${args}', None)
        self.fill(variables)
        if args is not None:
            self.fill_args(args)

    def fill(self, variables):
        command = [Template(_).safe_substitute(variables) for _ in self]
        self.clear()
        self.extend(command)
        return self

    def fill_name(self, name):
        return self.fill({'name': name})

    def fill_build(self, build):
        return self.fill({'build': build})

    def fill_args(self, args):
        self.args = args
        command = []
        for arg in self:
            if arg != '${args}':
                command.append(arg)
            else:
                command.extend(map(str, args))
        self.clear()
        self.extend(command)
        return self

    def copy(self):
        return type(self)(super().copy())


@total_ordering
class Executor:
    def __init__(self, name, args, executors, settings, program_path):
        self.name = name
        self.args = args

        self.executors = executors
        self.settings = settings
        self.program_path = program_path

        self.commands = [cmd.copy().fill_args(args)
                         for cmd in executors[name]['start']]

        self.compilation_required = 'compile' in executors[name]
        self.compiler = executors[name].get('compile', None)

        self.full_time = 0
        self.iters = 0

    def __repr__(self):
        return '<Executor %s [%s]: %f>' % (
            self.name, ', '.join(map(str, self.args)), self.time)

    def __le__(self, other):
        return self.full_time < other.full_time

    def __eq__(self, other):
        return self.full_time == other.full_time

    def call(self):
        for command in self.commands:
            start_time = time()
            status = sp.call(command, stdout=sp.DEVNULL)
            end_time = time()
            if status:
                raise ValueError('non zero exit program code %r' %
                                 ' '.join(command))
            self.full_time += end_time - start_time
        self.iters += 1

    def compile(self):
        if not self.compilation_required:
            return
        self.compilation_required = False

        if self.compiler is None:
            return
        for command in self.compiler:
            command.fill_name(self.program_path)

            # print(' '.join(command))
            status = sp.call(
                command,
                stdout=sp.DEVNULL, stderr=sp.DEVNULL)
            if status:
                sp.call(command)
                raise ValueError(
                    "Can't execute command %r" % ' '.join(command))

    @property
    def finished(self):
        return self.full_time > self.settings['exec_time']

    @property
    def time(self):
        return self.full_time / self.iters if self.iters else -1


def read_settings(path):
    if not os.path.exists(path):
        return {}

    with open(path) as settings_file:
        text = settings_file.read()

    return json.loads(text, object_pairs_hook=OrderedDict)


def get_programs(path):
    programs = [os.path.join(path, program) for program in os.listdir(path)]
    return list(filter(os.path.isdir, programs))


def get_executors(settings, variables):
    executors = {
        name: {
            'start': [
                Command(cmd, variables) for cmd in value['start']],
            'compile': [
                Command(cmd, variables) for cmd in value.get('compile', [])],
            'requirements': [
                Command(cmd, variables) for cmd in value.get('requirements', [])],
        } for name, value in settings['executors'].items()}
    return executors


def check_executors(executors):
    failed = set()
    for executor, settings in executors.items():
        for req in settings['requirements']:
            try:
                sp.call(req, stderr=sp.DEVNULL, stdout=sp.DEVNULL)
            except FileNotFoundError:
                failed.add(executor)
                logging.warning(
                    'command %r not found (%s would be skipped)',
                    req, executor)
    return failed


def run_executors(path, settings, executors, skipped_executors):
    average_time = settings['exec_time']
    time_limit = settings['time_limit']
    args = settings['args']
    if not args:
        args = [[]]

    programs = os.listdir(path)

    queue = []
    logging.info('Compilation')
    for program in programs:
        executor_name = program.rsplit('.', 1)[0]
        program = os.path.join(path, program)

        if (executor_name in skipped_executors or
                os.path.basename(program) == 'settings.json'):
            continue
        if executor_name not in executors:
            logging.warning('executor %s not found', executor_name)
            continue

        for command in executors[executor_name]['start']:
            command.fill_name(program)

        for i, arg in enumerate(args):
            executor = Executor(
                name=executor_name,
                args=arg,
                executors=executors,
                settings=settings,
                program_path=program)
            if i == 0:
                executor.compile()
            queue.append(executor)

    heapq.heapify(queue)

    results = []

    logging.info('Executing')
    while queue:
        executor = heapq.heappop(queue)

        # print(' '.join(command))
        executor.call()

        if executor.finished:
            results.append(executor)
            continue

        heapq.heappush(queue, executor)

    def key(executor):
        return executor.name

    results.sort(key=key)

    return {
        'program': os.path.basename(path),
        'data': {
            e_name: list(sorted(e, key=lambda e: e.args)) # TODO: keep args order
            for e_name, e in groupby(results, key)
        }}


def run_programs(programs=None, executors=None, skipped_executors=None):
    if skipped_executors is None:
        skipped_executors = set()
    skipped_executors = set(skipped_executors)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    programs_dir = os.path.join(base_dir, 'programs')

    build_dir = os.path.join(base_dir, 'build')
    os.makedirs(build_dir, exist_ok=True)

    all_programs = get_programs(programs_dir)

    global_settings = read_settings(
        os.path.join(programs_dir, 'settings.json'))
    global_settings.setdefault('build_dir', build_dir)

    filled_executors = get_executors(global_settings, {
        'build': global_settings['build_dir']
    })

    skipped_executors = skipped_executors | check_executors(filled_executors)
    if executors is not None:
        skipped_executors.update(
            [e for e in filled_executors if e not in executors])

    results = []
    for program in all_programs:
        if programs is not None and os.path.basename(program) not in programs:
            continue

        local_settings = read_settings(
            os.path.join(program, 'settings.json'))
        local_settings['args'] = local_settings.get('args', [])

        settings = deepcopy(global_settings)
        settings.update(local_settings)

        result = run_executors(
            program, settings, filled_executors, skipped_executors)
        if result is None:
            break

        pprint(result)
        results.append(result)
    return results


def main():
    run_programs(['sum'], executors=['java', 'c++', 'node-js'])


if __name__ == '__main__':
    main()
