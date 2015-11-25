"""develop tests
"""
import os
import site
import sys
import io

import pytest

from setuptools.command.develop import develop
from setuptools.dist import Distribution
from . import contexts
from setuptools.compat import PY3


SETUP_PY = """\
from setuptools import setup

setup(name='foo',
    packages=['foo'],
    use_2to3=True,
)
"""

INIT_PY = """print "foo"
"""

@pytest.yield_fixture
def temp_user(monkeypatch):
    with contexts.tempdir() as user_base:
        with contexts.tempdir() as user_site:
            monkeypatch.setattr('site.USER_BASE', user_base)
            monkeypatch.setattr('site.USER_SITE', user_site)
            yield


@pytest.yield_fixture
def test_env(tmpdir, temp_user):
    target = tmpdir
    foo = target.mkdir('foo')
    setup = target / 'setup.py'
    if setup.isfile():
        raise ValueError(dir(target))
    with setup.open('w') as f:
        f.write(SETUP_PY)
    init = foo / '__init__.py'
    with init.open('w') as f:
        f.write(INIT_PY)
    with target.as_cwd():
        yield target


class TestDevelop:
    @pytest.mark.skipif(hasattr(sys, 'real_prefix'),
        reason="Cannot run when invoked in a virtualenv")
    def test_2to3_user_mode(self, test_env):
        settings = dict(
            name='foo',
            packages=['foo'],
            use_2to3=True,
            version='0.0',
        )
        dist = Distribution(settings)
        dist.script_name = 'setup.py'
        cmd = develop(dist)
        cmd.user = 1
        cmd.ensure_finalized()
        cmd.install_dir = site.USER_SITE
        cmd.user = 1
        with contexts.quiet():
            cmd.run()

        # let's see if we got our egg link at the right place
        content = os.listdir(site.USER_SITE)
        content.sort()
        assert content == ['easy-install.pth', 'foo.egg-link']

        # Check that we are using the right code.
        fn = os.path.join(site.USER_SITE, 'foo.egg-link')
        with io.open(fn) as egg_link_file:
            path = egg_link_file.read().split()[0].strip()
        fn = os.path.join(path, 'foo', '__init__.py')
        with io.open(fn) as init_file:
            init = init_file.read().strip()

        expected = 'print("foo")' if PY3 else 'print "foo"'
        assert init == expected
