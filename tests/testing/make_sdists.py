#!/usr/bin/env python
"""
Build a collection of packages, to be used as a pytest fixture.

This script is reentrant IFF the destinations are not shared.
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from subprocess import check_call
from sys import executable as python


def info(*msg):
    from sys import stdout
    stdout.write(' '.join(str(x) for x in msg))
    stdout.write('\n')
    stdout.flush()


def make_copy(setuppy, dst):
    pkg = setuppy.dirpath().basename

    # unlike sdist, egg-info is reentrant-safe
    check_call(
        (python, 'setup.py', '--quiet', 'egg_info'),
        cwd=setuppy.dirname,
    )

    from glob import glob
    sources = setuppy.dirpath().join('*/SOURCES.txt')
    sources, = glob(str(sources))
    sources = open(sources).read().splitlines()

    copy = dst.join('src', pkg).ensure(dir=True)
    for source in sources:
        source = setuppy.dirpath().join(source)
        dest = copy.join(source.relto(setuppy))
        dest.dirpath().ensure(dir=True)
        source.copy(dest)
    return copy


def sdist(setuppy, dst):
    info('sdist', setuppy.dirpath().basename)
    copy = make_copy(setuppy, dst)
    check_call(
        (python, 'setup.py', '--quiet', 'sdist', '--dist-dir', str(dst)),
        cwd=str(copy),
    )


def build_one(src, dst):
    setuppy = src.join('setup.py')
    if setuppy.exists():
        sdist(setuppy, dst)

        if src.join('wheelme').exists():
            copy = make_copy(setuppy, dst)
            wheel(copy, dst)

        return True


def build_all(sources, dst):
    for source in sources:
        if build_one(source, dst):
            continue
        for source in sorted(source.listdir()):
            if not source.check(dir=True):
                continue

            build_one(source, dst)


class public_pypi_enabled(object):
    orig = None

    def __enter__(self):
        from os import environ
        self.orig = environ.pop('PIP_INDEX_URL', None)

    def __exit__(self, value, type_, traceback):
        from os import environ
        if self.orig is not None:
            environ['PIP_INDEX_URL'] = self.orig


def wheel(src, dst):
    info('wheel', src)

    with public_pypi_enabled():
        build = dst.join('build')
        check_call((
            python, '-m', 'pip.__main__',
            'wheel',
            '--quiet',
            '--build-dir', str(build),
            '--wheel-dir', str(dst),
            str(src)
        ))
        build.remove()  # pip1.5 wheel doesn't clean up its build =/


def download_sdist(source, destination):
    info('download sdist', source)
    with public_pypi_enabled():
        check_call((
            python, '-m', 'pip.__main__',
            'install',
            '--quiet',
            '--no-deps',
            '--no-use-wheel',
            '--build-dir', str(destination.join('build')),
            '--download', str(destination),
            str(source),
        ))


def make_sdists(sources, destination):
    build_all(sources, destination)
    wheel('argparse', destination)
    wheel('coverage-enable-subprocess', destination)
    download_sdist('coverage', destination)
    download_sdist('coverage-enable-subprocess', destination)


def main():
    from sys import argv
    argv = argv[1:]
    sources, destination = argv[:-1], argv[-1]

    from py._path.local import LocalPath
    sources = tuple([
        LocalPath(src) for src in sources
    ])
    destination = LocalPath(destination)

    return make_sdists(sources, destination)


if __name__ == '__main__':
    exit(main())
