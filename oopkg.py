import shutil

import os
from os import path
from pathlib import Path

from telex import git, auth, plugin, packagerepo

PKG_INSTALL_DIR="pkgs/installed"

class OneOffPackageManager(plugin.TelexPlugin):
    """
    Install One Off Packages in Telex
    """
    patterns = {
        "^{prefix}oo?pkg? install (?P<pkg_name>\S*) (?P<location>\S*)$": "install",
        "^{prefix}oo?pkg? uninstall (?P<pkg_name>\S*)$": "uninstall",
    }

    usage = {
        "{prefix}oopkg install spyfall /home/user/telex-plugins/spyfall: Installs the telex-spyfall plugin directly",
        "{prefix}oopkg uninstall spyfall: Removes the spyfall ",
    }

    def _copy_directory(self, src, dest):
        if os.name == "posix":
            # We can symlink
            try:
                os.symlink(src, dest)
            except OSError as e:
                return "Could not symlink. Error: %s" % e
            return "Symlinked!"
        else:
            try:
                shutil.copytree(src, dest)
            except shutil.Error as e:
                return 'Could not install. Error: %s' % e
            except OSError as e:
                return 'Could not install. Error: %s' % e
            return "Successfully copied"

    def _unlink(self, src):
        try:
            os.unlink(src)
        except OSError as e:
            rmattempt = self._rmtree(src)
            return "Could not remove symlink. Error: {}\nTrying to rm instead\n{}".format(str(e), rmattempt)
        return "Removed symlink"

    def _rmtree(self, src):
        try:
            shutil.rmtree(src)
        except shutil.Error as e:
            return 'Could not delete. Error: %s' % e
        except OSError as e:
            return 'Could not delete. Error: %s' % e
        return "Successfully deleted"

    def _rm_directory(self, src):
        if os.name == "posix":
            return self._unlink(src)
        else:
            return self._rmtree(src)

    def _pkg_repo_path(self, pkg_name):
        return path.join(PKG_INSTALL_DIR, pkg_name)

    @auth.authorize(groups=["admins"])
    def install(self, msg, matches):
        pkg_name = matches.groupdict()['pkg_name']
        location = matches.groupdict()['location']

        pkg_inst_path = Path(PKG_INSTALL_DIR)
        if not pkg_inst_path.exists():
            pkg_inst_path.mkdir(parents=True)

        destination = self._pkg_repo_path(pkg_name)

        if not location.startswith("http"):
            result = self._copy_directory(location, destination)
            self.respond_to_msg(msg, result)

        else:
            gs = git.clone(location, pkg_name, cwd=str(pkg_inst_path))
            if gs.has_error():
                self.respond_to_msg(msg, "Error installing package \"{}\"\n{}{}".format(pkg_name, gs.stdout, gs.stderr))
                return

            pkg_req_path = pkg_inst_path / pkg_name / "repository" / "requirements.txt"
            # print('\n\n{}\n\n'.format(pkg_req_path))
            if pkg_req_path.exists():
                pip.main(['install', '--upgrade', '-r', str(pkg_req_path)])

            self.reload_plugins()

            self.plugin_manager.collectPlugins()
            self.respond_to_msg(msg, "{}{}\nSuccessfully installed package: {}".format(gs.stdout, gs.stderr, pkg_name))


    @auth.authorize(groups=["admins"])
    def uninstall(self, msg, matches):
        pkg_name = matches.groupdict()['pkg_name']

        destination = self._pkg_repo_path(pkg_name)

        if not Path(destination).exists():
            return "the plugin doesn't exist"

        result = self._rm_directory(destination)

        self.respond_to_msg(msg, result)

    def reload_plugins(self):
        self.plugin_manager.collectPlugins()
        return "Plugins reloaded"
