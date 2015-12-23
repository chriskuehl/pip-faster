#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''\
usage: venv-update [-h] [virtualenv_dir] [requirements [requirements ...]]

Update a (possibly non-existant) virtualenv directory using a requirements.txt listing
When this script completes, the virtualenv should have the same packages as if it were
removed, then rebuilt.

To set the index server, export a PIP_INDEX_URL variable.
    See also: https://pip.readthedocs.org/en/stable/user_guide/#environment-variables

positional arguments:
  virtualenv_dir  Destination virtualenv directory (default: virtualenv_run)
  requirements    Requirements files. (default: requirements.txt)

optional arguments:
  -h, --help      show this help message and exit

Version control at: https://github.com/yelp/pip-faster
'''
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from os.path import exists
from os.path import join

DEFAULT_VIRTUALENV_PATH = 'virtualenv_run'
VENV_UPDATE_REQS_OVERRIDE = 'requirements.d/venv-update.txt'
__version__ = '1.0rc2.dev1'

# This script must not rely on anything other than
#   stdlib>=2.6 and virtualenv>1.11


def parseargs(args):
    """extremely rudimentary arg parsing, to handle --help and find the virtualenv path"""
    if set(args) & set(('-h', '--help')):
        print(__doc__, end='')
        exit(0)

    for arg in args:
        if arg == '--':
            break
        elif arg.startswith('-'):
            continue
        else:
            return arg

    return DEFAULT_VIRTUALENV_PATH


def timid_relpath(arg):
    """convert an argument to a relative path, carefully"""
    from os.path import isabs, relpath, sep
    if isabs(arg):
        result = relpath(arg)
        if result.count(sep) + 1 < arg.count(sep):
            return result

    return arg


def shellescape(args):
    from pipes import quote
    return ' '.join(quote(timid_relpath(arg)) for arg in args)


def colorize(cmd):
    from os import isatty

    if isatty(1):
        template = '\033[01;36m>\033[m \033[01;32m{0}\033[m'
    else:
        template = '> {0}'

    return template.format(shellescape(cmd))


def run(cmd):
    from subprocess import check_call
    check_call(('echo', colorize(cmd)))
    check_call(cmd)


def info(msg):
    # use a subprocess to ensure correct output interleaving.
    from subprocess import check_call
    check_call(('echo', msg))


def samefile(file1, file2):
    if not exists(file1) or not exists(file2):
        return False
    else:
        from os.path import samefile
        return samefile(file1, file2)


def user_cache_dir():
    # stolen from pip.utils.appdirs.user_cache_dir
    from os import getenv
    from os.path import expanduser
    return getenv('XDG_CACHE_HOME', expanduser('~/.cache'))


def exec_(cmd):
    info('exec' + colorize(cmd))

    from os import execv
    execv(cmd[0], cmd)  # never returns


def exec_intermediate_virtualenv(args):
    scratch = join(user_cache_dir(), 'venv-update')
    intermediate_virtualenv = join(scratch, 'venv')
    python = venv_python(intermediate_virtualenv)

    if not exists(python):
        run(('virtualenv', intermediate_virtualenv))
    if not exists(join(scratch, 'virtualenv.py')):
        run(('pip', 'install', '--target', scratch, 'virtualenv'))

    venv_update = join(scratch, 'venv-update')
    if not exists(venv_update):
        run(('cp', dotpy(__file__), venv_update))

    if samefile(dotpy(__file__), venv_update):
        return  # all done!
    else:
        exec_((python, venv_update,) + args)


def get_python_version(interpreter):
    if not exists(interpreter):
        return None

    cmd = (interpreter, '-c', 'import sys; print(sys.version)')

    from subprocess import Popen, PIPE, CalledProcessError
    interpreter = Popen(cmd, stdout=PIPE)
    output, _ = interpreter.communicate()
    if interpreter.returncode:
        raise CalledProcessError(interpreter.returncode, cmd)
    else:
        return output


def ensure_virtualenv(args):
    """Ensure we have a valid virtualenv."""
    import virtualenv

    class notlocal(object):
        venv_path = None
        pip_args = None

    def adjust_options(options, virtualenv_args):
        # TODO-TEST: proper error message with no arguments
        if virtualenv_args:
            venv_path = notlocal.venv_path = virtualenv_args[0]
        else:
            venv_path = notlocal.venv_path = DEFAULT_VIRTUALENV_PATH
            virtualenv_args[:] = [venv_path]

        if venv_path == DEFAULT_VIRTUALENV_PATH or options.prompt == '<dirname>':
            from os.path import basename, dirname
            options.prompt = '(%s)' % basename(dirname(venv_path))

        notlocal.pip_args = tuple(virtualenv_args[1:])
        if not notlocal.pip_args:
            notlocal.pip_args = ('-r', 'requirements.txt')
        del virtualenv_args[1:]

        # there are (potentially) *three* python interpreters involved here:
        # 1) the interpreter we're currently using
        from sys import executable as current_python
        # 2) the interpreter we're instructing virtualenv to copy
        if options.python:
            source_python = virtualenv.resolve_interpreter(options.python)
        else:
            source_python = current_python
        # 3) the interpreter virtualenv will create
        destination_python = venv_python(venv_path)

        source_version = get_python_version(source_python)
        destination_version = get_python_version(destination_python)

        if source_version == destination_version:
            raise SystemExit(0)  # looks good! we're done here.

        if exists(destination_python):
            info('Removing invalidated virtualenv.')
            run(('rm', '-rf', venv_path))

        if not samefile(current_python, source_python):
            exec_((source_python, dotpy(__file__)) + args)  # never returns

    # this is actually a documented extension point:
    #   http://virtualenv.readthedocs.org/en/latest/reference.html#adjust_options
    virtualenv.adjust_options = adjust_options

    raise_on_failure(virtualenv.main)
    return notlocal.venv_path, notlocal.pip_args


def wait_for_all_subprocesses():
    from os import wait
    try:
        while True:
            wait()
    except OSError as error:
        if error.errno == 10:  # no child processes
            return
        else:
            raise


def touch(filename, timestamp):
    """set the mtime of a file"""
    if timestamp is not None:
        timestamp = (timestamp, timestamp)  # atime, mtime

    from os import utime
    utime(filename, timestamp)


def mark_venv_valid(venv_path):
    wait_for_all_subprocesses()
    touch(venv_path, None)


def mark_venv_invalid(venv_path):
    # LBYL, to attempt to avoid any exception during exception handling
    from os.path import isdir
    if venv_path is not None and isdir(venv_path):
        info('')
        info("Something went wrong! Sending '%s' back in time, so make knows it's invalid." % timid_relpath(venv_path))
        info('Waiting for all subprocesses to finish...')
        wait_for_all_subprocesses()
        info('DONE')
        touch(venv_path, 0)
        info('')


def dotpy(filename):
    if filename.endswith(('.pyc', '.pyo', '.pyd')):
        return filename[:-1]
    else:
        return filename


def venv_executable(venv_path, executable):
    return join(venv_path, 'bin', executable)


def venv_python(venv_path):
    return venv_executable(venv_path, 'python')


class CacheOpts(object):

    def __init__(self):
        # We put the cache in the directory that pip already uses.
        # This has better security characteristics than a machine-wide cache, and is a
        #   pattern people can use for open-source projects
        self.pipdir = user_cache_dir() + '/pip-faster'
        # We could combine these caches to one directory, but pip would search everything twice, going slower.
        self.download_cache = self.pipdir + '/download'
        self.wheelhouse = self.pipdir + '/wheelhouse'

        self.pip_options = (
            '--download-cache=' + self.download_cache,
            '--find-links=file://' + self.wheelhouse,
        )


def venv_update(args):
    """we have an arbitrary python interpreter active, (possibly) outside the virtualenv we want.

    make a fresh venv at the right spot, make sure it has pip-faster, and use it
    """
    exec_intermediate_virtualenv(args)
    # invariant: virtualenv (the library) is importable
    # invariant: we're not currently using the destination python

    venv_path, pip_options = ensure_virtualenv(args)
    # invariant: the final virtualenv exists, with the right python version

    python = venv_python(venv_path)
    if not exists(python):
        return 'virtualenv executable not found: %s' % python

    pip_install = (python, '-m', 'pip.__main__', 'install') + CacheOpts().pip_options

    if exists(VENV_UPDATE_REQS_OVERRIDE):
        args = ('-r', VENV_UPDATE_REQS_OVERRIDE)
    else:
        args = ('pip-faster==' + __version__,)

    # TODO: short-circuit when pip-faster is already there.
    run(pip_install + args)
    run((python, '-m', 'pip_faster', 'install', '--prune', '--upgrade') + pip_options)


def raise_on_failure(mainfunc):
    """raise if and only if mainfunc fails"""
    from subprocess import CalledProcessError
    try:
        errors = mainfunc()
        if errors:
            exit(errors)
    except CalledProcessError as error:
        exit(error.returncode)
    except SystemExit as error:
        if error.code:
            raise
    except KeyboardInterrupt:  # I don't plan to test-cover this.  :pragma:nocover:
        exit(1)


def main():
    from sys import argv
    args = tuple(argv[1:])
    venv_path = parseargs(args)

    try:
        raise_on_failure(lambda: venv_update(args))
    except BaseException:
        mark_venv_invalid(venv_path)
        raise
    else:
        mark_venv_valid(venv_path)


if __name__ == '__main__':
    exit(main())
