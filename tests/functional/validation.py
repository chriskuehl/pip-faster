from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from sys import executable as python

import pytest

from testing import enable_coverage
from testing import Path
from testing import pip_freeze
from testing import requirements
from testing import run
from testing import TOP
from testing import venv_update
from testing import venv_update_symlink_pwd


def assert_c_extension_runs():
    out, err = run('venv/bin/c-extension-script')
    assert err == ''
    assert out == 'hello world\n'

    out, err = run('sh', '-c', '. venv/bin/activate && c-extension-script')
    assert err == ''
    assert out == 'hello world\n'


def assert_python_version(version):
    out, err = run('sh', '-c', '. venv/bin/activate && python --version')
    assert out == ''
    assert err.startswith(version)


@pytest.mark.usefixtures('pypi_server')
def test_python_versions(tmpdir):
    tmpdir.chdir()
    requirements('project-with-c')

    def run_with_coverage(*options):
        enable_coverage(tmpdir, options=options)
        venv_update(*options)

    run_with_coverage('--python=python2.6')
    assert_c_extension_runs()
    assert_python_version('Python 2.6')

    run_with_coverage('--python=python2.7')
    assert_c_extension_runs()
    assert_python_version('Python 2.7')

    run_with_coverage('--python=python2.6')
    assert_c_extension_runs()
    assert_python_version('Python 2.6')


@pytest.mark.usefixtures('pypi_server')
def test_virtualenv_moved(tmpdir):
    """if you move the virtualenv and venv-update again, the old will be blown away, and things will work"""
    original_path = 'original'
    new_path = 'new_dir'

    with tmpdir.mkdir(original_path).as_cwd():
        requirements('project_with_c')
        venv_update()
        assert_c_extension_runs()

    with tmpdir.as_cwd():
        Path(original_path).rename(new_path)

    with tmpdir.join(new_path).as_cwd():
        with pytest.raises(OSError) as excinfo:
            assert_c_extension_runs()
        # python >= 3.3 raises FileNotFoundError
        assert excinfo.type.__name__ in ('OSError', 'FileNotFoundError')
        assert excinfo.value.args[0] == 2  # no such file

        venv_update()
        assert_c_extension_runs()


@pytest.mark.usefixtures('pypi_server')
def test_recreate_active_virtualenv(tmpdir):
    with tmpdir.as_cwd():
        run('virtualenv', '--python', python, 'venv')
        run('venv/bin/pip', 'install', '-r', str(TOP / 'requirements.d/coverage.txt'))

        requirements('project_with_c')
        venv_update_symlink_pwd()
        run('venv/bin/python', 'venv_update.py')

        assert_c_extension_runs()


@pytest.mark.usefixtures('pypi_server')
def test_update_while_active(tmpdir):
    tmpdir.chdir()
    requirements('virtualenv<2')

    venv_update()
    assert 'project-with-c' not in pip_freeze()

    # An arbitrary small package: project_with_c
    requirements('project_with_c')

    venv_update_symlink_pwd()
    out, err = run('sh', '-c', '. venv/bin/activate && python venv_update.py')

    assert err == ''
    assert out.startswith('Keeping virtualenv from previous run.\n')
    assert 'project-with-c' in pip_freeze()


@pytest.mark.usefixtures('pypi_server')
def test_update_invalidated_while_active(tmpdir):
    tmpdir.chdir()
    requirements('virtualenv<2')

    venv_update()
    assert 'project-with-c' not in pip_freeze()

    # An arbitrary small package: project_with_c
    requirements('project-with-c')

    venv_update_symlink_pwd()
    out, err = run('sh', '-c', '. venv/bin/activate && python venv_update.py --system-site-packages')

    assert err == ''
    assert out.startswith('Removing invalidated virtualenv.\n')
    assert 'project-with-c' in pip_freeze()


@pytest.mark.usefixtures('pypi_server')
def it_gives_the_same_python_version_as_we_started_with(tmpdir):
    python = 'venv/bin/python'

    def get_version(outputs):
        assert '' in outputs
        return ''.join(outputs)

    with tmpdir.as_cwd():
        run('virtualenv', '--python', 'python3.3', 'venv')
        initial_version = get_version(run(python, '--version'))
        assert initial_version.startswith('Python 3.3.')

        requirements('')
        venv_update_symlink_pwd()
        out, err = run(python, 'venv_update.py')

        assert err == ''
        assert out.startswith('Removing invalidated virtualenv.\n')

        final_version = get_version(run(python, '--version'))
        assert final_version == initial_version
