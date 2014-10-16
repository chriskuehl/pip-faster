from py._path.local import LocalPath as Path
import pytest

TOP = Path(__file__) / '../../..'
SCENARIOS = TOP/'testing/data/scenarios'


def run(*cmd, **env):
    from pipes import quote
    from subprocess import check_call

    if env:
        from os import environ
        tmp = env
        env = environ.copy()
        env.update(tmp)
    else:
        env = None

    check_call(('echo', '\033[01;36m>\033[m \033[01;33m{0}\033[m'.format(
        ' '.join(quote(arg) for arg in cmd)
    )))
    check_call(cmd, env=env)


def do_install(pwd, tmpdir):
    run(
        'coverage',
        'run',
        '--parallel-mode',
        '--rcfile', str(TOP/'.coveragerc'),
        '-m', 'venv_update',
        COVERAGE_FILE=str(pwd/'.coverage'),
        HOME=str(tmpdir),
    )


def test_trivial(tmpdir):
    pwd = Path('.').realpath()
    tmpdir.chdir()

    # Trailing slash is essential to rsync
    run('rsync', '-a', str(SCENARIOS) + '/trivial/', '.')
    do_install(pwd, tmpdir)

    pwd.chdir()


# Not yet installed: https://github.com/klrmn/pytest-rerunfailures
@pytest.mark.flaky(reruns=10)
def test_second_install_faster(tmpdir):
    """install twice, and the second one should be faster, due to whl caching"""
    pwd = Path('.').realpath()
    tmpdir.chdir()

    # Trailing slash is essential to rsync
    run('rsync', '-a', str(SCENARIOS) + '/trivial/', '.')
    with open('requirements.txt', 'w') as requirements:
        # Something with significant C parts: lxml
        # Should I make my own fake c-extention just to remove this dependency?
        requirements.write('lxml')

    from time import time
    start = time()
    do_install(pwd, tmpdir)
    time1 = time() - start

    start = time()
    do_install(pwd, tmpdir)
    time2 = time() - start

    pwd.chdir()

    # second install should be at least twice as fast
    ratio = time1 / time2
    print '%.1fx speedup' % ratio
    assert ratio / 2
