from distutils.command.install_scripts import install_scripts \
     as _install_scripts
from easy_install import get_script_args
from pkg_resources import Distribution, PathMetadata, ensure_directory
import os
from distutils import log


class install_scripts(_install_scripts):
    """Do normal script install, plus any egg_info wrapper scripts"""

    def run(self):
        self.run_command("egg_info")
        _install_scripts.run(self)  # run first to set up self.outfiles

        ei_cmd = self.get_finalized_command("egg_info")       
        dist = Distribution(
            ei_cmd.egg_base, PathMetadata(ei_cmd.egg_base, ei_cmd.egg_info),
            ei_cmd.egg_name, ei_cmd.egg_version,
        )
        for args in get_script_args(dist):
            self.write_script(*args)

    def write_script(self, script_name, contents, mode="t", *ignored):
        """Write an executable file to the scripts directory"""

        log.info("Installing %s script to %s", script_name, self.install_dir)
        target = os.path.join(self.install_dir, script_name)
        self.outfiles.append(target)

        if not self.dry_run:
            ensure_directory(target)
            f = open(target,"w"+mode)
            f.write(contents)
            f.close()
            try:
                os.chmod(target,0755)
            except (AttributeError, os.error):
                pass

