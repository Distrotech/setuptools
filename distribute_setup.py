#!python
"""Bootstrap distribute installation

If you want to use setuptools in your package's setup.py, just include this
file in the same directory with it, and add this to the top of your setup.py::

    from distribute_setup import use_setuptools
    use_setuptools()

If you want to require a specific version of setuptools, set a download
mirror, or use an alternate download directory, you can do so by supplying
the appropriate options to ``use_setuptools()``.

This file can also be run as a script to install or upgrade setuptools.
"""
import sys
import os
import shutil
import time
import fnmatch
from distutils import log
from distutils.errors import DistutilsError

is_jython = sys.platform.startswith('java')
if is_jython:
    import subprocess

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

DEFAULT_VERSION = "0.6"
DEFAULT_URL     = "http://pypi.python.org/packages/%s/d/distribute/" % sys.version[:3]

md5_data = {
    'distribute-0.6-py2.3.egg': '66d06db7fc91227585f81b0b27b07bab',
    'distribute-0.6-py2.4.egg': '8fc3eb887ee98c506c38838955f9eee2',
    'distribute-0.6-py2.5.egg': 'd87f6492c53d192c62e0334859d18b59',
    'distribute-0.6-py2.6.egg': '89c46c2ed0c756dd278acc1482aa12f1',
}

def _validate_md5(egg_name, data):
    if egg_name in md5_data:
        digest = md5(data).hexdigest()
        if digest != md5_data[egg_name]:
            print >>sys.stderr, (
                "md5 validation of %s failed!  (Possible download problem?)"
                % egg_name
            )
            sys.exit(2)
    return data

def use_setuptools(
    version=DEFAULT_VERSION, download_base=DEFAULT_URL, to_dir=os.curdir,
    download_delay=15
):
    """Automatically find/download setuptools and make it available on sys.path

    `version` should be a valid setuptools version number that is available
    as an egg for download under the `download_base` URL (which should end with
    a '/').  `to_dir` is the directory where setuptools will be downloaded, if
    it is not already available.  If `download_delay` is specified, it should
    be the number of seconds that will be paused before initiating a download,
    should one be required.  If an older version of setuptools is installed,
    this routine will print a message to ``sys.stderr`` and raise SystemExit in
    an attempt to abort the calling script.
    """
    was_imported = 'pkg_resources' in sys.modules or 'setuptools' in sys.modules
    def do_download():
        egg = download_setuptools(version, download_base, to_dir, download_delay)
        sys.path.insert(0, egg)
        import setuptools; setuptools.bootstrap_install_from = egg
    try:
        import pkg_resources
        if not hasattr(pkg_resources, '_distribute'):
            raise ImportError
    except ImportError:
        return do_download()
    try:
        pkg_resources.require("distribute>="+version); return
    except pkg_resources.VersionConflict, e:
        if was_imported:
            print >>sys.stderr, (
            "The required version of distribute (>=%s) is not available, and\n"
            "can't be installed while this script is running. Please install\n"
            " a more recent version first, using 'easy_install -U distribute'."
            "\n\n(Currently using %r)"
            ) % (version, e.args[0])
            sys.exit(2)
        else:
            del pkg_resources, sys.modules['pkg_resources']    # reload ok
            return do_download()
    except pkg_resources.DistributionNotFound:
        return do_download()

def download_setuptools(
    version=DEFAULT_VERSION, download_base=DEFAULT_URL, to_dir=os.curdir,
    delay = 15
):
    """Download distribute from a specified location and return its filename

    `version` should be a valid distribute version number that is available
    as an egg for download under the `download_base` URL (which should end
    with a '/'). `to_dir` is the directory where the egg will be downloaded.
    `delay` is the number of seconds to pause before an actual download attempt.
    """
    import urllib2, shutil
    egg_name = "distribute-%s-py%s.egg" % (version,sys.version[:3])
    url = download_base + egg_name
    saveto = os.path.join(to_dir, egg_name)
    src = dst = None
    if not os.path.exists(saveto):  # Avoid repeated downloads
        try:
            from distutils import log
            if delay:
                log.warn("""
---------------------------------------------------------------------------
This script requires distribute version %s to run (even to display
help).  I will attempt to download it for you (from
%s), but
you may need to enable firewall access for this script first.
I will start the download in %d seconds.

(Note: if this machine does not have network access, please obtain the file

   %s

and place it in this directory before rerunning this script.)
---------------------------------------------------------------------------""",
                    version, download_base, delay, url
                ); from time import sleep; sleep(delay)
            log.warn("Downloading %s", url)
            src = urllib2.urlopen(url)
            # Read/write all in one block, so we don't create a corrupt file
            # if the download is interrupted.
            data = _validate_md5(egg_name, src.read())
            dst = open(saveto,"wb"); dst.write(data)
        finally:
            if src: src.close()
            if dst: dst.close()
    return os.path.realpath(saveto)


SETUPTOOLS_PKG_INFO  = """\
Metadata-Version: 1.0
Name: setuptools
Version: 0.6c9
Summary: xxxx
Home-page: xxx
Author: xxx
Author-email: xxx
License: xxx
Description: xxx
"""

def _patch_file(path, content):
    """Will backup the file then patch it"""
    existing_content = open(path).read()
    if existing_content == content:
        # already patched
        log.warn('Already patched.')
        return False
    log.warn('Patching...')
    os.rename(path, path +'.OLD.%s' % time.time())
    f = open(path, 'w')
    try:
        f.write(content)
    finally:
        f.close()
    return True

def _same_content(path, content):
    return open(path).read() == content

def _rename_path(path):
    new_name = path + '.OLD.%s' % time.time()
    log.warn('Renaming %s into %s' % (path, new_name))
    os.rename(path, new_name)
    return new_name

def _remove_flat_installation(placeholder):
    if not os.path.isdir(placeholder):
        log.warn('Unkown installation at %s' % placeholder)
        return False
    found = False
    for file in os.listdir(placeholder):
        if fnmatch.fnmatch(file, 'setuptools*.egg-info'):
            found = True
            break
    if not found:
        log.warn('Could not locate setuptools*.egg-info')
    else:
        log.warn('Removing elements out of the way...')
        pkg_info = os.path.join(placeholder, file)
        if os.path.isdir(pkg_info):
            patched = _patch_egg_dir(pkg_info)
        else:
            patched = _patch_file(pkg_info, SETUPTOOLS_PKG_INFO)

    if not patched:
        log.warn('%s already patched.' % pkg_info)
        return False
    # now let's move the files out of the way
    for element in ('setuptools', 'pkg_resources.py', 'site.py'):
        element = os.path.join(placeholder, element)
        if os.path.exists(element):
            _rename_path(element)
        else:
            log.warn('Could not find the %s element of the '
                     'Setuptools distribution' % element)
    return True

def after_install(dist):
    log.warn('After install bootstrap.')
    placeholder = dist.get_command_obj('install').install_purelib
    if not os.path.exists(placeholder):
        log.warn('Could not find the install location')
        return
    pyver = '%s.%s' % (sys.version_info[0], sys.version_info[1])
    setuptools_file = 'setuptools-0.6c9-py%s.egg-info' % pyver
    pkg_info = os.path.join(placeholder, setuptools_file)
    if os.path.exists(pkg_info):
        log.warn('%s already exists' % pkg_info)
        return
    log.warn('Creating %s' % pkg_info)
    f = open(pkg_info, 'w')
    try:
        f.write(SETUPTOOLS_PKG_INFO)
    finally:
        f.close()
    pth_file = os.path.join(placeholder, 'setuptools.pth')
    log.warn('Creating %s' % pth_file)
    f = open(pth_file, 'w')
    try:
        f.write(os.path.join(os.curdir, setuptools_file))
    finally:
        f.close()

def _patch_egg_dir(path):
    # let's check if it's already patched
    pkg_info = os.path.join(path, 'EGG-INFO', 'PKG-INFO')
    if os.path.exists(pkg_info):
        if _same_content(pkg_info, SETUPTOOLS_PKG_INFO):
            log.warn('%s already patched.' % pkg_info)
            return False
    _rename_path(path)
    os.mkdir(path)
    os.mkdir(os.path.join(path, 'EGG-INFO'))
    pkg_info = os.path.join(path, 'EGG-INFO', 'PKG-INFO')
    f = open(pkg_info, 'w')
    try:
        f.write(SETUPTOOLS_PKG_INFO)
    finally:
        f.close()
    return True

def before_install():
    log.warn('Before install bootstrap.')
    fake_setuptools()

def fake_setuptools():
    log.warn('Scanning installed packages')
    try:
        import pkg_resources
    except ImportError:
        # we're cool
        log.warn('Setuptools or Distribute does not seem to be installed.')
        return
    ws = pkg_resources.working_set
    setuptools_dist = ws.find(pkg_resources.Requirement.parse('setuptools'))
    if setuptools_dist is None:
        log.warn('No setuptools distribution found')
        return
    # detecting if it was already faked
    setuptools_location = setuptools_dist.location
    log.warn('Setuptools installation detected at %s' % setuptools_location)

    # let's see if its an egg
    if not setuptools_location.endswith('.egg'):
        log.warn('Non-egg installation')
        res = _remove_flat_installation(setuptools_location)
        if not res:
            return
    else:
        log.warn('Egg installation')
        pkg_info = os.path.join(setuptools_location, 'EGG-INFO', 'PKG-INFO')
        if (os.path.exists(pkg_info) and
            _same_content(pkg_info, SETUPTOOLS_PKG_INFO)):
            log.warn('Already patched.')
            return
        log.warn('Patching...')
        # let's create a fake egg replacing setuptools one
        res = _patch_egg_dir(setuptools_location)
        if not res:
            return
    log.warn('Patched done.')
    _relaunch()

def _relaunch():
    log.warn('Relaunching...')
    # we have to relaunch the process
    args = [sys.executable]  + sys.argv
    if is_jython:
        sys.exit(subprocess.call(args))
    else:
        sys.exit(os.spawnv(os.P_WAIT, sys.executable, args))

def _easy_install(argv, egg=None):
    from setuptools import setup
    from setuptools.dist import Distribution
    import distutils.core
    if egg is not None:
        setup_args = list(argv) + ['-v'] + [egg]
    else:
        setup_args = list(argv)
    try:
        return setup(script_args = ['-q','easy_install',
                                    '-v'] + setup_args,
                    script_name = sys.argv[0] or 'easy_install',
                    distclass=Distribution)
    except DistutilsError:
        return sys.exit(2)

def main(argv, version=DEFAULT_VERSION):
    """Install or upgrade setuptools and EasyInstall"""
    # let's deactivate any existing setuptools installation first
    fake_setuptools()
    try:
        import setuptools
        # we need to check if the installed setuptools
        # is from Distribute or from setuptools
        if not hasattr(setuptools, '_distribute'):
            # now we are ready to install distribute
            raise ImportError
    except ImportError:
        egg = None
        try:
            egg = download_setuptools(version, delay=0)
            sys.path.insert(0, egg)
            import setuptools
            if not hasattr(setuptools, '_distribute'):
                placeholder = os.path.split(os.path.dirname(setuptools.__file__))[0]
                if not placeholder.endswith('.egg'):
                    res = _remove_flat_installation(placeholder)
                    if res:
                        _relaunch()
                print >> sys.stderr, (
                "The patch didn't work, Setuptools is still active.\n"
                "Possible reason: your have a system-wide setuptools installed "
                "and you are in a virtualenv.\n"
                "If you are inside a virtualenv, make sure you used the --no-site-packages option"
                )
                sys.exit(2)
            dist = _easy_install(argv, egg)
            after_install(dist)
            return
            #from setuptools.command import easy_install
            #try:
            #    return easy_install.main(list(argv)+['-v']+[egg])
            #except DistutilsError:
            #    return sys.exit(2)
        finally:
            if egg and os.path.exists(egg):
                os.unlink(egg)
    else:
        if setuptools.__version__ == '0.0.1':
            print >>sys.stderr, (
            "You have an obsolete version of setuptools installed.  Please\n"
            "remove it from your system entirely before rerunning this script."
            )
            sys.exit(2)

    req = "distribute>="+version
    import pkg_resources
    try:
        pkg_resources.require(req)
    except pkg_resources.VersionConflict:
        try:
            _easy_install(argv, [download_setuptools(delay=0)])
            #from setuptools.command.easy_install import main
        except ImportError:
            from easy_install import main
            main(list(argv)+[download_setuptools(delay=0)])
        sys.exit(0) # try to force an exit
    else:
        if argv:
            _easy_install(argv)
            #from setuptools.command.easy_install import main
            #main(argv)
        else:
            print "distribute version",version,"or greater has been installed."
            print '(Run "distribute_setup.py -U distribute" to reinstall or upgrade.)'

def update_md5(filenames):
    """Update our built-in md5 registry"""

    import re

    for name in filenames:
        base = os.path.basename(name)
        f = open(name,'rb')
        md5_data[base] = md5(f.read()).hexdigest()
        f.close()

    data = ["    %r: %r,\n" % it for it in md5_data.items()]
    data.sort()
    repl = "".join(data)

    import inspect
    srcfile = inspect.getsourcefile(sys.modules[__name__])
    f = open(srcfile, 'rb'); src = f.read(); f.close()

    match = re.search("\nmd5_data = {\n([^}]+)}", src)
    if not match:
        print >>sys.stderr, "Internal error!"
        sys.exit(2)

    src = src[:match.start(1)] + repl + src[match.end(1):]
    f = open(srcfile,'w')
    f.write(src)
    f.close()


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--md5update':
        update_md5(sys.argv[2:])
    else:
        main(sys.argv[1:])

