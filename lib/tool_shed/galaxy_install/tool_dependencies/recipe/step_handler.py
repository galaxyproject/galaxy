import hashlib
import logging
import os
import re
import shutil
import stat
import tarfile
import tempfile
import zipfile
from string import Template

# TODO: eliminate the use of fabric here.
from fabric.api import lcd, settings

from galaxy.util import (
    asbool,
    download_to_file
)
from galaxy.util.compression_utils import CompressedFile
from galaxy.util.template import fill_template
from tool_shed.galaxy_install.tool_dependencies.env_manager import EnvManager
from tool_shed.util import basic_util, tool_dependency_util

log = logging.getLogger(__name__)

VIRTUALENV_URL = 'https://pypi.python.org/packages/d4/0c/9840c08189e030873387a73b90ada981885010dd9aea134d6de30cd24cb8/virtualenv-15.1.0.tar.gz'


class Download(object):

    def url_download(self, install_dir, downloaded_file_name, download_url, extract=True, checksums={}):
        """
        The given download_url can have an extension like #md5#, #sha256#, (or #md5= to support pypi defaults).

            https://pypi.python.org/packages/source/k/khmer/khmer-1.0.tar.gz#md5#b60639a8b2939836f66495b9a88df757

        Alternatively, to not break HTTP spec, you can specify md5 and
        sha256 as keys in the <action /> element.

        This indicates a checksum which will be checked after download.
        If the checksum does not match an exception is thrown.
        """
        file_path = os.path.join(install_dir, downloaded_file_name)
        try:
            download_to_file(download_url, file_path, chunk_size=basic_util.CHUNK_SIZE)
        except Exception as e:
            err_msg = 'Error downloading from URL %s : %s' % (str(download_url), str(e))
            raise Exception(err_msg)

        if 'sha256sum' in checksums or '#sha256#' in download_url:
            downloaded_checksum = hashlib.sha256(open(file_path, 'rb').read()).hexdigest().lower()

            # Determine expected value
            if 'sha256sum' in checksums:
                expected = checksums['sha256sum'].lower()
            else:
                expected = download_url.split('#sha256#')[1].lower()

            if downloaded_checksum != expected:
                raise Exception('Given sha256 checksum does not match with the one from the downloaded file (%s != %s).' % (downloaded_checksum, expected))

        if 'md5sum' in checksums or '#md5#' in download_url or '#md5=' in download_url:
            downloaded_checksum = hashlib.md5(open(file_path, 'rb').read()).hexdigest().lower()

            # Determine expected value
            if 'md5sum' in checksums:
                expected = checksums['md5sum'].lower()
            else:
                expected = re.split('#md5[#=]', download_url)[1].lower()

            if downloaded_checksum != expected:
                raise Exception('Given md5 checksum does not match with the one from the downloaded file (%s != %s).' % (downloaded_checksum, expected))

        if extract:
            if tarfile.is_tarfile(file_path) or (zipfile.is_zipfile(file_path) and not file_path.endswith('.jar')):
                archive = CompressedFile(file_path)
                extraction_path = archive.extract(install_dir)
            else:
                extraction_path = os.path.abspath(install_dir)
        else:
            extraction_path = os.path.abspath(install_dir)

        return extraction_path

    def get_elem_checksums(self, elem):
        rval = {}
        for hash_type in ('md5sum', 'sha256sum'):
            if hash_type in elem.keys():
                rval[hash_type] = elem.get(hash_type).lower()
        return rval

    def get_dict_checksums(self, dct):
        return dict(i for i in dct.items() if i[0] in ['md5sum', 'sha256sum'])


class RecipeStep(object):
    """Abstract class that defines a standard format for handling recipe steps when installing packages."""

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        raise Exception("Unimplemented Method")

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        raise Exception("Unimplemented Method")


class AssertDirectoryExecutable(RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'assert_directory_executable'

    def assert_directory_executable(self, full_path):
        """
        Return True if a symbolic link or directory exists and is executable, but if
        full_path is a file, return False.
        """
        if full_path is None:
            return False
        if os.path.isfile(full_path):
            return False
        if os.path.isdir(full_path):
            # Make sure the owner has execute permission on the directory.
            # See https://docs.python.org/2/library/stat.html
            if stat.S_IXUSR & os.stat(full_path)[stat.ST_MODE] == 64:
                return True
        return False

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Make sure a symbolic link or directory on disk exists and is executable, but is not a file.
        Since this class is not used in the initial download stage, no recipe step filtering is
        performed here, and None values are always returned for filtered_actions and dir.
        """
        if os.path.isabs(action_dict['full_path']):
            full_path = action_dict['full_path']
        else:
            full_path = os.path.join(current_dir, action_dict['full_path'])
        if not self.assert_directory_executable(full_path=full_path):
            status = self.app.install_model.ToolDependency.installation_status.ERROR
            error_message = 'The path %s is not a directory or is not executable by the owner.' % str(full_path)
            tool_dependency = tool_dependency_util.set_tool_dependency_attributes(self.app,
                                                                                  tool_dependency,
                                                                                  status=status,
                                                                                  error_message=error_message)
        return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # <action type="assert_executable">$INSTALL_DIR/mira/my_file</action>
        if action_elem.text:
            action_dict['full_path'] = basic_util.evaluate_template(action_elem.text, install_environment)
        return action_dict


class AssertDirectoryExists(RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'assert_directory_exists'

    def assert_directory_exists(self, full_path):
        """
        Return True if a symbolic link or directory exists, but if full_path is a file,
        return False.
        """
        if full_path is None:
            return False
        if os.path.isfile(full_path):
            return False
        if os.path.isdir(full_path):
            return True
        return False

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Make sure a a symbolic link or directory on disk exists, but is not a file.  Since this
        class is not used in the initial download stage, no recipe step filtering is performed
        here, and None values are always returned for filtered_actions and dir.
        """
        if os.path.isabs(action_dict['full_path']):
            full_path = action_dict['full_path']
        else:
            full_path = os.path.join(current_dir, action_dict['full_path'])
        if not self.assert_directory_exists(full_path=full_path):
            status = self.app.install_model.ToolDependency.installation_status.ERROR
            error_message = 'The path %s is not a directory or does not exist.' % str(full_path)
            tool_dependency = tool_dependency_util.set_tool_dependency_attributes(self.app,
                                                                                  tool_dependency,
                                                                                  status=status,
                                                                                  error_message=error_message)
        return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # <action type="make_directory">$INSTALL_DIR/mira</action>
        if action_elem.text:
            action_dict['full_path'] = basic_util.evaluate_template(action_elem.text, install_environment)
        return action_dict


class AssertFileExecutable(RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'assert_file_executable'

    def assert_file_executable(self, full_path):
        """
        Return True if a symbolic link or file exists and is executable, but if full_path
        is a directory, return False.
        """
        if full_path is None:
            return False
        if os.path.isdir(full_path):
            return False
        if os.path.exists(full_path):
            # Make sure the owner has execute permission on the file.
            # See https://docs.python.org/2/library/stat.html
            if stat.S_IXUSR & os.stat(full_path)[stat.ST_MODE] == 64:
                return True
        return False

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Make sure a symbolic link or file on disk exists and is executable, but is not a directory.
        Since this class is not used in the initial download stage, no recipe step filtering is
        performed here, and None values are always returned for filtered_actions and dir.
        """
        if os.path.isabs(action_dict['full_path']):
            full_path = action_dict['full_path']
        else:
            full_path = os.path.join(current_dir, action_dict['full_path'])
        if not self.assert_file_executable(full_path=full_path):
            status = self.app.install_model.ToolDependency.installation_status.ERROR
            error_message = 'The path %s is not a file or is not executable by the owner.' % str(full_path)
            tool_dependency = tool_dependency_util.set_tool_dependency_attributes(self.app,
                                                                                  tool_dependency,
                                                                                  status=status,
                                                                                  error_message=error_message)
        return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # <action type="assert_executable">$INSTALL_DIR/mira/my_file</action>
        if action_elem.text:
            action_dict['full_path'] = basic_util.evaluate_template(action_elem.text, install_environment)
        return action_dict


class AssertFileExists(RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'assert_file_exists'

    def assert_file_exists(self, full_path):
        """
        Return True if a symbolic link or file exists, but if full_path is a directory,
        return False.
        """
        if full_path is None:
            return False
        if os.path.isdir(full_path):
            return False
        if os.path.exists(full_path):
            return True
        return False

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Make sure a symbolic link or file on disk exists, but is not a directory.  Since this
        class is not used in the initial download stage, no recipe step filtering is performed
        here, and None values are always returned for filtered_actions and dir.
        """
        if os.path.isabs(action_dict['full_path']):
            full_path = action_dict['full_path']
        else:
            full_path = os.path.join(current_dir, action_dict['full_path'])
        if not self.assert_file_exists(full_path=full_path):
            status = self.app.install_model.ToolDependency.installation_status.ERROR
            error_message = 'The path %s is not a file or does not exist.' % str(full_path)
            tool_dependency = tool_dependency_util.set_tool_dependency_attributes(self.app,
                                                                                  tool_dependency,
                                                                                  status=status,
                                                                                  error_message=error_message)
        return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # <action type="assert_on_path">$INSTALL_DIR/mira/my_file</action>
        if action_elem.text:
            action_dict['full_path'] = basic_util.evaluate_template(action_elem.text, install_environment)
        return action_dict


class Autoconf(RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'autoconf'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Handle configure, make and make install in a shell, allowing for configuration options.  Since this
        class is not used in the initial download stage, no recipe step filtering is performed here, and None
        values are always returned for filtered_actions and dir.
        """
        with settings(warn_only=True):
            configure_opts = action_dict.get('configure_opts', '')
            if 'prefix=' in configure_opts:
                pre_cmd = './configure %s && make && make install' % configure_opts
            else:
                pre_cmd = './configure --prefix=$INSTALL_DIR %s && make && make install' % configure_opts
            cmd = install_environment.build_command(basic_util.evaluate_template(pre_cmd, install_environment))
            install_environment.handle_command(tool_dependency=tool_dependency,
                                               cmd=cmd,
                                               return_output=False,
                                               job_name=package_name)
            # The caller should check the status of the returned tool_dependency since this function
            # does nothing with the return_code.
            return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # Handle configure, make and make install allow providing configuration options
        if action_elem.text:
            configure_opts = basic_util.evaluate_template(action_elem.text, install_environment)
            action_dict['configure_opts'] = configure_opts
        return action_dict


class ChangeDirectory(RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'change_directory'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Change the working directory in a shell.  Since this class is not used in the initial download stage,
        no recipe step filtering is performed here and a None value is return for filtered_actions.  However,
        the new dir value is returned since it is needed for later steps.
        """

        def dir_valid(test_dir):
            """
            Make sure the defined directory is within current_dir or work_dir.
            """
            for valid_dir in [os.path.realpath(current_dir), os.path.realpath(work_dir)]:
                if test_dir.startswith(valid_dir) and os.path.exists(test_dir):
                    return True
            return False

        target_dir = os.path.realpath(os.path.normpath(action_dict['directory']))
        if dir_valid(target_dir):
            # We have a directory that includes a path.
            dir = target_dir
        else:
            target_dir = os.path.realpath(os.path.normpath(os.path.join(current_dir, action_dict['directory'])))
            if dir_valid(target_dir):
                dir = target_dir
            else:
                log.debug('Invalid or nonexistent directory %s specified, ignoring change_directory action.', str(action_dict['directory']))
                dir = current_dir
        return tool_dependency, None, dir

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # <action type="change_directory">PHYLIP-3.6b</action>
        if action_elem.text:
            action_dict['directory'] = basic_util.evaluate_template(action_elem.text, install_environment)
        return action_dict


class Chmod(RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'chmod'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Change the mode setting for certain files in the installation environment.  Since this class is not
        used in the initial download stage, no recipe step filtering is performed here, and None values are
        always returned for filtered_actions and dir.
        """
        for target_file, mode in action_dict['change_modes']:
            if os.path.exists(target_file):
                os.chmod(target_file, mode)
            else:
                log.debug('Invalid file %s specified, ignoring %s action.', target_file, self.type)
        return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # Change the read, write, and execute bits on a file.
        # <action type="chmod">
        #   <file mode="750">$INSTALL_DIR/bin/faToTwoBit</file>
        # </action>
        file_elems = action_elem.findall('file')
        chmod_actions = []
        # A unix octal mode is the sum of the following values:
        # Owner:
        # 400 Read    200 Write    100 Execute
        # Group:
        # 040 Read    020 Write    010 Execute
        # World:
        # 004 Read    002 Write    001 Execute
        for file_elem in file_elems:
            # So by the above table, owner read/write/execute and group read permission would be 740.
            # Python's os.chmod uses base 10 modes, convert received unix-style octal modes to base 10.
            received_mode = int(file_elem.get('mode', 600), base=8)
            # For added security, ensure that the setuid and setgid bits are not set.
            mode = received_mode & ~(stat.S_ISUID | stat.S_ISGID)
            file = basic_util.evaluate_template(file_elem.text, install_environment)
            chmod_tuple = (file, mode)
            chmod_actions.append(chmod_tuple)
        if chmod_actions:
            action_dict['change_modes'] = chmod_actions
        return action_dict


class DownloadBinary(Download, RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'download_binary'

    def download_binary(self, url, work_dir, checksums):
        """Download a pre-compiled binary from the specified URL."""
        downloaded_filename = os.path.split(url)[-1]
        self.url_download(work_dir, downloaded_filename, url, extract=False, checksums=checksums)
        return downloaded_filename

    def filter_actions_after_binary_installation(self, actions):
        '''Filter out actions that should not be processed if a binary download succeeded.'''
        filtered_actions = []
        for action in actions:
            action_type, action_dict = action
            if action_type in ['set_environment', 'chmod', 'download_binary']:
                filtered_actions.append(action)
        return filtered_actions

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Download a binary file.  If the value of initial_download is True, the recipe steps will be
        filtered and returned and the installation directory (i.e., dir) will be defined and returned.
        If we're not in the initial download stage, these actions will not occur, and None values will
        be returned for them.
        """
        url = action_dict['url']
        # Get the target directory for this download if the user has specified one. Default to the root of $INSTALL_DIR.
        target_directory = action_dict.get('target_directory', None)
        # Attempt to download a binary from the specified URL.
        downloaded_filename = None
        try:
            checksums = self.get_dict_checksums(action_dict)
            log.debug('Attempting to download from %s to %s', url, str(target_directory))
            downloaded_filename = self.download_binary(url, work_dir, checksums)
            if initial_download:
                # Filter out any actions that are not download_binary, chmod, or set_environment.
                filtered_actions = self.filter_actions_after_binary_installation(actions[1:])
                # Set actions to the same, so that the current download_binary doesn't get re-run in the
                # next stage.  TODO: this may no longer be necessary...
                actions = [item for item in filtered_actions]
        except Exception as e:
            log.exception(str(e))
            if initial_download:
                # No binary exists, or there was an error downloading the binary from the generated URL.
                # Filter the actions so that stage 2 can proceed with the remaining actions.
                filtered_actions = actions[1:]
                action_type, action_dict = filtered_actions[0]
        # If the downloaded file exists, move it to $INSTALL_DIR. Put this outside the try/catch above so that
        # any errors in the move step are correctly sent to the tool dependency error handler.
        if downloaded_filename and os.path.exists(os.path.join(work_dir, downloaded_filename)):
            if target_directory:
                target_directory = os.path.realpath(os.path.normpath(os.path.join(install_environment.install_dir,
                                                                                  target_directory)))
                # Make sure the target directory is not outside of $INSTALL_DIR.
                if target_directory.startswith(os.path.realpath(install_environment.install_dir)):
                    full_path_to_dir = os.path.abspath(os.path.join(install_environment.install_dir, target_directory))
                else:
                    full_path_to_dir = os.path.abspath(install_environment.install_dir)
            else:
                full_path_to_dir = os.path.abspath(install_environment.install_dir)
            basic_util.move_file(current_dir=work_dir,
                                 source=downloaded_filename,
                                 destination=full_path_to_dir)
        # Not sure why dir is ignored in this method, need to investigate...
        dir = None
        if initial_download:
            return tool_dependency, filtered_actions, dir
        return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        platform_info_dict = tool_dependency_util.get_platform_info_dict()
        platform_info_dict['name'] = str(tool_dependency.name)
        platform_info_dict['version'] = str(tool_dependency.version)
        url_template_elems = action_elem.findall('url_template')
        # Check if there are multiple url_template elements, each with attrib entries for a specific platform.
        if len(url_template_elems) > 1:
            # <base_url os="darwin" extract="false">
            #     http://hgdownload.cse.ucsc.edu/admin/exe/macOSX.${architecture}/faToTwoBit
            # </base_url>
            # This method returns the url_elem that best matches the current platform as received from os.uname().
            # Currently checked attributes are os and architecture.  These correspond to the values sysname and
            # processor from the Python documentation for os.uname().
            url_template_elem = tool_dependency_util.get_download_url_for_platform(url_template_elems, platform_info_dict)
        else:
            url_template_elem = url_template_elems[0]
        action_dict['url'] = Template(url_template_elem.text.strip()).safe_substitute(platform_info_dict)
        action_dict['target_directory'] = action_elem.get('target_directory', None)
        action_dict.update(self.get_elem_checksums(action_elem))
        return action_dict


class DownloadByUrl(Download, RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'download_by_url'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Download a file via HTTP.  If the value of initial_download is True, the recipe steps will be
        filtered and returned and the installation directory (i.e., dir) will be defined and returned.
        If we're not in the initial download stage, these actions will not occur, and None values will
        be returned for them.
        """
        if initial_download:
            # Eliminate the download_by_url action so remaining actions can be processed correctly.
            filtered_actions = actions[1:]
        url = action_dict['url']
        is_binary = action_dict.get('is_binary', False)
        if 'target_filename' in action_dict:
            # Sometimes compressed archives extract their content to a folder other than the default
            # defined file name.  Using this attribute will ensure that the file name is set appropriately
            # and can be located after download, decompression and extraction.
            downloaded_filename = action_dict['target_filename']
        else:
            downloaded_filename = os.path.split(url)[-1]

        checksums = self.get_dict_checksums(action_dict)
        log.debug('Attempting to download via url: %s', url)
        dir = self.url_download(work_dir, downloaded_filename, url, extract=True, checksums=checksums)
        if is_binary:
            log_file = os.path.join(install_environment.install_dir, basic_util.INSTALLATION_LOG)
            if os.path.exists(log_file):
                logfile = open(log_file, 'ab')
            else:
                logfile = open(log_file, 'wb')
            logfile.write('Successfully downloaded from url: %s\n' % action_dict['url'])
            logfile.close()
        log.debug('Successfully downloaded from url: %s' % action_dict['url'])
        if initial_download:
            return tool_dependency, filtered_actions, dir
        return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # <action type="download_by_url">
        #     http://sourceforge.net/projects/samtools/files/samtools/0.1.18/samtools-0.1.18.tar.bz2
        # </action>
        #
        # <action type="download_by_url" md5sum="71dab132e21c0766f0de84c2371a9157" sha256sum="f3faaf34430d4782956562eb72906289e8e34d44d0c4d73837bdbeead7746b16">
        #     http://sourceforge.net/projects/samtools/files/samtools/0.1.18/samtools-0.1.18.tar.bz2
        # </action>
        if is_binary_download:
            action_dict['is_binary'] = True
        if action_elem.text:
            action_dict['url'] = action_elem.text.strip()
            target_filename = action_elem.get('target_filename', None)
            if target_filename:
                action_dict['target_filename'] = target_filename
        action_dict.update(self.get_elem_checksums(action_elem))
        return action_dict


class DownloadFile(Download, RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'download_file'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Download a file.  If the value of initial_download is True, the recipe steps will be
        filtered and returned and the installation directory (i.e., dir) will be defined and returned.
        If we're not in the initial download stage, these actions will not occur, and None values will
        be returned for them.
        """
        # <action type="download_file">http://effectors.org/download/version/TTSS_GUI-1.0.1.jar</action>
        # Download a single file to the working directory.
        if initial_download:
            filtered_actions = actions[1:]
        url = action_dict['url']
        if 'target_filename' in action_dict:
            # Sometimes compressed archives extracts their content to a folder other than the default
            # defined file name.  Using this attribute will ensure that the file name is set appropriately
            # and can be located after download, decompression and extraction.
            filename = action_dict['target_filename']
        else:
            filename = url.split('/')[-1]
        if current_dir is not None:
            work_dir = current_dir
        checksums = self.get_dict_checksums(action_dict)
        log.debug('Attempting to download via url: %s', url)
        self.url_download(work_dir, filename, url, extract=action_dict['extract'], checksums=checksums)
        if initial_download:
            dir = os.path.curdir
            return tool_dependency, filtered_actions, dir
        return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # <action type="download_file">http://effectors.org/download/version/TTSS_GUI-1.0.1.jar</action>
        if action_elem.text:
            action_dict['url'] = action_elem.text.strip()
            target_filename = action_elem.get('target_filename', None)
            if target_filename:
                action_dict['target_filename'] = target_filename
            action_dict['extract'] = asbool(action_elem.get('extract', False))
        action_dict.update(self.get_elem_checksums(action_elem))
        return action_dict


class MakeDirectory(RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'make_directory'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Make a directory on disk.  Since this class is not used in the initial download stage, no recipe step
        filtering is performed here, and None values are always returned for filtered_actions and dir.
        """
        if os.path.isabs(action_dict['full_path']):
            full_path = action_dict['full_path']
        else:
            full_path = os.path.join(current_dir, action_dict['full_path'])
        self.make_directory(full_path=full_path)
        return tool_dependency, None, None

    def make_directory(self, full_path):
        if not os.path.exists(full_path):
            os.makedirs(full_path)

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # <action type="make_directory">$INSTALL_DIR/lib/python</action>
        if action_elem.text:
            action_dict['full_path'] = basic_util.evaluate_template(action_elem.text, install_environment)
        return action_dict


class MakeInstall(RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'make_install'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Execute a make_install command in a shell.  Since this class is not used in the initial download stage,
        no recipe step filtering is performed here, and None values are always returned for filtered_actions and dir.
        """
        # make; make install; allow providing make options
        with settings(warn_only=True):
            make_opts = action_dict.get('make_opts', '')
            cmd = install_environment.build_command('make %s && make install' % make_opts)
            install_environment.handle_command(tool_dependency=tool_dependency,
                                               cmd=cmd,
                                               return_output=False,
                                               job_name=package_name)
            # The caller should check the status of the returned tool_dependency since this function
            # does nothing with the return_code.
            return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # make; make install; allow providing make options
        if action_elem.text:
            make_opts = basic_util.evaluate_template(action_elem.text, install_environment)
            action_dict['make_opts'] = make_opts
        return action_dict


class MoveDirectoryFiles(RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'move_directory_files'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Move a directory of files.  Since this class is not used in the initial download stage, no recipe step
        filtering is performed here, and None values are always returned for filtered_actions and dir.
        """
        self.move_directory_files(current_dir=current_dir,
                                  source_dir=os.path.join(action_dict['source_directory']),
                                  destination_dir=os.path.join(action_dict['destination_directory']))
        return tool_dependency, None, None

    def move_directory_files(self, current_dir, source_dir, destination_dir):
        source_directory = os.path.abspath(os.path.join(current_dir, source_dir))
        destination_directory = os.path.abspath(os.path.join(destination_dir))
        if not os.path.isdir(destination_directory):
            os.makedirs(destination_directory)
        for dir_entry in os.listdir(source_directory):
            source_entry = os.path.join(source_directory, dir_entry)
            if os.path.islink(source_entry):
                destination_entry = os.path.join(destination_directory, dir_entry)
                os.symlink(os.readlink(source_entry), destination_entry)
                os.remove(source_entry)
            else:
                shutil.move(source_entry, destination_directory)

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # <action type="move_directory_files">
        #     <source_directory>bin</source_directory>
        #     <destination_directory>$INSTALL_DIR/bin</destination_directory>
        # </action>
        for move_elem in action_elem:
            move_elem_text = basic_util.evaluate_template(move_elem.text, install_environment)
            if move_elem_text:
                action_dict[move_elem.tag] = move_elem_text
        return action_dict


class MoveFile(RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'move_file'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Move a file on disk.  Since this class is not used in the initial download stage, no recipe step
        filtering is performed here, and None values are always returned for filtered_actions and dir.
        """
        basic_util.move_file(current_dir=current_dir,
                             source=os.path.join(action_dict['source']),
                             destination=os.path.join(action_dict['destination']),
                             rename_to=action_dict['rename_to'])
        return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # <action type="move_file" rename_to="new_file_name">
        #     <source>misc/some_file</source>
        #     <destination>$INSTALL_DIR/bin</destination>
        # </action>
        action_dict['source'] = basic_util.evaluate_template(action_elem.find('source').text, install_environment)
        action_dict['destination'] = basic_util.evaluate_template(action_elem.find('destination').text, install_environment)
        action_dict['rename_to'] = action_elem.get('rename_to')
        return action_dict


class RegexReplace(RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'regex_replace'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        r"""
        Search and replace text in a file using regular expressions. Since this class is not used in the initial
        download stage, no recipe step filtering is performed here, and None values are always returned for
        filtered_actions and dir.

        This step supports the full range of python's regular expression engine, including backreferences in
        the replacement text. Example::

            <action type="regex_replace" filename="Makefile">
                <regex>^CFLAGS(\s*)=\s*-g\s*-Wall\s*-O2\s*$$</regex>
                <replacement>CFLAGS\1= -g -Wall -O2 -I$$(NCURSES_INCLUDE_PATH)/ncurses/ -I$$(NCURSES_INCLUDE_PATH) -L$$(NCURSES_LIB_PATH)</replacement>
            </action>

        Before::

            CFLAGS  = -g -Wall -O2

        After::

            CFLAGS  = -g -Wall -O2 -I$(NCURSES_INCLUDE_PATH)/ncurses/ -I$(NCURSES_INCLUDE_PATH) -L$(NCURSES_LIB_PATH)
        """
        log_file = os.path.join(install_environment.install_dir, basic_util.INSTALLATION_LOG)
        if os.path.exists(log_file):
            logfile = open(log_file, 'ab')
        else:
            logfile = open(log_file, 'wb')
        if os.path.isabs(action_dict['filename']):
            filename = action_dict['filename']
            if not (filename.startswith(current_dir) or filename.startswith(install_environment.install_dir)):
                return tool_dependency, None, None
        else:
            filename = os.path.abspath(os.path.join(current_dir, action_dict['filename']))
        regex = re.compile(action_dict['regex'])
        replacement = action_dict['replacement']
        temp_fh = tempfile.NamedTemporaryFile(dir=current_dir)
        ofh = temp_fh.file
        total_replacements = 0
        with open(filename, 'r') as haystack:
            for line in haystack:
                altered_text, replacement_count = re.subn(regex, replacement, line)
                if replacement_count > 0:
                    ofh.write(altered_text)
                    total_replacements += replacement_count
                else:
                    ofh.write(line)
            ofh.flush()
        shutil.copyfile(temp_fh.name, filename)
        log_text = 'Successfully replaced pattern %s with text %s in file %s: %s replacements made\n'
        log_text = log_text % (action_dict['regex'], action_dict['replacement'], filename, total_replacements)
        log.debug(log_text)
        logfile.write(log_text)
        logfile.close()
        return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        '''
        Populate action_dict with the provided filename, regex, and replacement text.
        '''
        action_dict['filename'] = basic_util.evaluate_template(action_elem.get('filename'), install_environment)
        action_dict['regex'] = basic_util.evaluate_template(action_elem.find('regex').text, install_environment)
        action_dict['replacement'] = basic_util.evaluate_template(action_elem.find('replacement').text, install_environment)
        return action_dict


class SetEnvironment(RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'set_environment'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Configure an install environment.  Since this class is not used in the initial download stage,
        no recipe step filtering is performed here, and None values are always returned for filtered_actions
        and dir.
        """
        # Currently the only action supported in this category is "environment_variable".
        cmds = install_environment.environment_commands('set_environment')
        env_var_dicts = action_dict.get('environment_variable', [])
        root_dir_dict = dict(action='set_to',
                             name='%s_ROOT_DIR' % re.sub(r"[^A-Z0-9_]", "_", tool_dependency.name.upper()),
                             value=install_environment.install_dir)
        env_var_dicts.append(root_dir_dict)
        for env_var_dict in env_var_dicts:
            # Check for the presence of the $ENV[] key string and populate it if possible.
            env_var_dict = self.handle_environment_variables(install_environment=install_environment,
                                                             tool_dependency=tool_dependency,
                                                             env_var_dict=env_var_dict,
                                                             set_prior_environment_commands=cmds)
            env_file_builder.append_line(**env_var_dict)
        # The caller should check the status of the returned tool_dependency since return_code is not
        # returned by this function.
        return tool_dependency, None, None

    def handle_environment_variables(self, install_environment, tool_dependency, env_var_dict,
                                     set_prior_environment_commands):
        """
        This method works with a combination of three tool dependency definition tag sets, which are defined in
        the tool_dependencies.xml file in the order discussed here.  The example for this discussion is the
        tool_dependencies.xml file contained in the osra repository, which is available at:

        https://testtoolshed.g2.bx.psu.edu/view/bgruening/osra

        The first tag set defines a complex repository dependency like this.  This tag set ensures that changeset
        revision XXX of the repository named package_graphicsmagick_1_3 owned by YYY in the tool shed ZZZ has been
        previously installed::

            <tool_dependency>
                <package name="graphicsmagick" version="1.3.18">
                    <repository changeset_revision="XXX" name="package_graphicsmagick_1_3" owner="YYY" prior_installation_required="True" toolshed="ZZZ" />
                </package>
                ...

        By the way, there is an env.sh file associated with version 1.3.18 of the graphicsmagick package which looks
        something like this (we'll reference this file later in this discussion)::

            GRAPHICSMAGICK_ROOT_DIR=/<my configured tool dependency path>/graphicsmagick/1.3.18/YYY/package_graphicsmagick_1_3/XXX/gmagick;
            export GRAPHICSMAGICK_ROOT_DIR

        The second tag set defines a specific package dependency that has been previously installed (guaranteed by the
        tag set discussed above) and compiled, where the compiled dependency is needed by the tool dependency currently
        being installed (osra version 2.0.0 in this case) and complied in order for its installation and compilation to
        succeed.  This tag set is contained within the <package name="osra" version="2.0.0"> tag set, which implies that
        version 2.0.0 of the osra package requires version 1.3.18 of the graphicsmagick package in order to successfully
        compile.  When this tag set is handled, one of the effects is that the env.sh file associated with graphicsmagick
        version 1.3.18 is "sourced", which undoubtedly sets or alters certain environment variables (e.g. PATH, PYTHONPATH,
        etc)::

            <!-- populate the environment variables from the dependent repositories -->
            <action type="set_environment_for_install">
                <repository changeset_revision="XXX" name="package_graphicsmagick_1_3" owner="YYY" toolshed="ZZZ">
                    <package name="graphicsmagick" version="1.3.18" />
                </repository>
            </action>

        The third tag set enables discovery of the same required package dependency discussed above for correctly compiling
        the osra version 2.0.0 package, but in this case the package can be discovered at tool execution time.  Using the
        $ENV[] option as shown in this example, the value of the environment variable named GRAPHICSMAGICK_ROOT_DIR (which
        was set in the environment using the second tag set described above) will be used to automatically alter the env.sh
        file associated with the osra version 2.0.0 tool dependency when it is installed into Galaxy.  * Refer to where we
        discussed the env.sh file for version 1.3.18 of the graphicsmagick package above::

            <action type="set_environment">
                <environment_variable action="prepend_to" name="LD_LIBRARY_PATH">$ENV[GRAPHICSMAGICK_ROOT_DIR]/lib/</environment_variable>
                <environment_variable action="prepend_to" name="LD_LIBRARY_PATH">$INSTALL_DIR/potrace/build/lib/</environment_variable>
                <environment_variable action="prepend_to" name="PATH">$INSTALL_DIR/bin</environment_variable>
                <!-- OSRA_DATA_FILES is only used by the galaxy wrapper and is not part of OSRA -->
                <environment_variable action="set_to" name="OSRA_DATA_FILES">$INSTALL_DIR/share</environment_variable>
            </action>

        The above tag will produce an env.sh file for version 2.0.0 of the osra package when it it installed into Galaxy
        that looks something like this.  Notice that the path to the gmagick binary is included here since it expands the
        defined $ENV[GRAPHICSMAGICK_ROOT_DIR] value in the above tag set::

            LD_LIBRARY_PATH=/<my configured tool dependency path>/graphicsmagick/1.3.18/YYY/package_graphicsmagick_1_3/XXX/gmagick/lib/:$LD_LIBRARY_PATH;
            export LD_LIBRARY_PATH
            LD_LIBRARY_PATH=/<my configured tool dependency path>/osra/1.4.0/YYY/depends_on/XXX/potrace/build/lib/:$LD_LIBRARY_PATH;
            export LD_LIBRARY_PATH
            PATH=/<my configured tool dependency path>/osra/1.4.0/YYY/depends_on/XXX/bin:$PATH;
            export PATH
            OSRA_DATA_FILES=/<my configured tool dependency path>/osra/1.4.0/YYY/depends_on/XXX/share;
            export OSRA_DATA_FILES
        """
        env_var_value = env_var_dict['value']
        # env_var_value is the text of an environment variable tag like this:
        # <environment_variable action="prepend_to" name="LD_LIBRARY_PATH">
        # Here is an example of what env_var_value could look like: $ENV[GRAPHICSMAGICK_ROOT_DIR]/lib/
        if '$ENV[' in env_var_value and ']' in env_var_value:
            # Pull out the name of the environment variable to populate.
            inherited_env_var_name = env_var_value.split('[')[1].split(']')[0]
            to_replace = '$ENV[%s]' % inherited_env_var_name
            found = False
            for env_cmd in set_prior_environment_commands:
                # LD_LIBRARY_PATH=/<my configured tool dependency path>/<some path>; export LD_LIBRARY_PATH
                if env_cmd.startswith(inherited_env_var_name):
                    env_val = env_cmd.split('=')[1]
                    # /<my configured tool dependency path>/<some path>; export LD_LIBRARY_PATH
                    env_val = env_val.split(';')[0]
                    # /<my configured tool dependency path>/<some path>
                    log.info('Replacing %s with %s in env.sh for this repository.', to_replace, env_val)
                    env_var_value = env_var_value.replace(to_replace, env_val)
                    found = True
                    break
            if not found:
                # Replace the original $ENV[] with nothing, to avoid any shell misparsings later on.
                log.debug('Environment variable %s not found, removing from set_environment.', inherited_env_var_name)
                env_var_value = env_var_value.replace(to_replace, '$%s' % inherited_env_var_name)
            env_var_dict['value'] = env_var_value
        return env_var_dict

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # This function is only called for set environment actions as defined above, not within a <set_environment> tool
        # dependency type. Here is an example of the tag set this function does handle:
        # <action type="set_environment">
        #     <environment_variable name="PYTHONPATH" action="append_to">$INSTALL_DIR/lib/python</environment_variable>
        #     <environment_variable name="PATH" action="prepend_to">$INSTALL_DIR/bin</environment_variable>
        # </action>
        # Here is an example of the tag set this function does not handle:
        # <action type="set_environment">
        #     <environment_variable name="PATH" action="prepend_to">$INSTALL_DIR</environment_variable>
        # </action>
        env_manager = EnvManager(self.app)
        env_var_dicts = []
        for env_elem in action_elem:
            if env_elem.tag == 'environment_variable':
                env_var_dict = env_manager.create_env_var_dict(elem=env_elem,
                                                               install_environment=install_environment)
                if env_var_dict:
                    env_var_dicts.append(env_var_dict)
        if env_var_dicts:
            # The last child of an <action type="set_environment"> might be a comment, so manually set it to be 'environment_variable'.
            action_dict['environment_variable'] = env_var_dicts
        return action_dict


class SetEnvironmentForInstall(RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'set_environment_for_install'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Configure an environment for compiling a package.  Since this class is not used in the initial
        download stage, no recipe step filtering is performed here, and None values are always returned
        for filtered_actions and dir.
        """
        # Currently the only action supported in this category is a list of paths to one or more tool
        # dependency env.sh files, the environment setting in each of which will be injected into the
        # environment for all <action type="shell_command"> tags that follow this
        # <action type="set_environment_for_install"> tag set in the tool_dependencies.xml file.
        env_shell_file_paths = action_dict.get('env_shell_file_paths', [])
        install_environment.add_env_shell_file_paths(env_shell_file_paths)
        return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # <action type="set_environment_for_install">
        #    <repository toolshed="http://localhost:9009/" name="package_numpy_1_7" owner="test" changeset_revision="c84c6a8be056">
        #        <package name="numpy" version="1.7.1" />
        #    </repository>
        # </action>
        # This action type allows for defining an environment that will properly compile a tool dependency.
        # Currently, tag set definitions like that above are supported, but in the future other approaches
        # to setting environment variables or other environment attributes can be supported.  The above tag
        # set will result in the installed and compiled numpy version 1.7.1 binary to be used when compiling
        # the current tool dependency package.  See the package_matplotlib_1_2 repository in the test tool
        # shed for a real-world example.
        all_env_shell_file_paths = []
        env_manager = EnvManager(self.app)
        for env_elem in action_elem:
            if env_elem.tag == 'repository':
                env_shell_file_paths = env_manager.get_env_shell_file_paths(env_elem)
                if env_shell_file_paths:
                    all_env_shell_file_paths.extend(env_shell_file_paths)
        action_dict['env_shell_file_paths'] = all_env_shell_file_paths
        return action_dict


class SetupPerlEnvironment(Download, RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'setup_perl_environment'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Initialize the environment for installing Perl packages.  The class is called during the initial
        download stage when installing packages, so the value of initial_download will generally be True.
        However, the parameter value allows this class to also be used in the second stage of the installation,
        although it may never be necessary.  If initial_download is True, the recipe steps will be filtered
        and returned and the installation directory (i.e., dir) will be defined and returned.  If we're not
        in the initial download stage, these actions will not occur, and None values will be returned for them.
        """
        # <action type="setup_perl_environment">
        #       <repository name="package_perl_5_18" owner="bgruening">
        #           <package name="perl" version="5.18.1" />
        #       </repository>
        #       <!-- allow downloading and installing an Perl package from cpan.org-->
        #       <package>XML::Parser</package>
        #       <package sha256sum="da8a88112bff0224bd17b74eb28f605f96db6481ed5c8c00ca7e851522deee2b">http://search.cpan.org/CPAN/authors/id/C/CJ/CJFIELDS/BioPerl-1.6.922.tar.gz</package>
        # </action>
        dir = None
        if initial_download:
            filtered_actions = actions[1:]
        env_shell_file_paths = action_dict.get('env_shell_file_paths', None)
        if env_shell_file_paths is None:
            log.debug('Missing Perl environment, make sure your specified Perl installation exists.')
            if initial_download:
                return tool_dependency, filtered_actions, dir
            return tool_dependency, None, None
        else:
            install_environment.add_env_shell_file_paths(env_shell_file_paths)
        log.debug('Handling setup_perl_environment for tool dependency %s with install_environment.env_shell_file_paths:\n%s' %
                  (str(tool_dependency.name), str(install_environment.env_shell_file_paths)))
        dir = os.path.curdir
        current_dir = os.path.abspath(os.path.join(work_dir, dir))
        with lcd(current_dir):
            with settings(warn_only=True):
                perl_packages = action_dict.get('perl_packages', [])
                for perl_package_dict in perl_packages:
                    perl_package = perl_package_dict['package']
                    # If set to a true value then MakeMaker's prompt function will always
                    # return the default without waiting for user input.
                    cmd = '''PERL_MM_USE_DEFAULT=1; export PERL_MM_USE_DEFAULT; '''
                    cmd += 'HOME=%s; export HOME; ' % work_dir
                    cmd += 'export PERL5LIB=$INSTALL_DIR/lib/perl5:$PERL5LIB;'
                    cmd += 'export PATH=$INSTALL_DIR/bin:$PATH;'
                    if perl_package.find('://') != -1:
                        # We assume a URL to a gem file.
                        url = perl_package
                        perl_package_name = url.split('/')[-1]
                        checksums = perl_package_dict.get('checksums', {})
                        dir = self.url_download(work_dir, perl_package_name, url, extract=True, checksums=checksums)
                        # Search for Build.PL or Makefile.PL (ExtUtils::MakeMaker vs. Module::Build).
                        tmp_work_dir = os.path.join(work_dir, dir)
                        if os.path.exists(os.path.join(tmp_work_dir, 'Makefile.PL')):
                            cmd += '''perl Makefile.PL INSTALL_BASE=$INSTALL_DIR && make && make install'''
                        elif os.path.exists(os.path.join(tmp_work_dir, 'Build.PL')):
                            cmd += '''perl Build.PL --install_base $INSTALL_DIR && perl Build && perl Build install'''
                        else:
                            log.debug('No Makefile.PL or Build.PL file found in %s. Skipping installation of %s.' %
                                (url, perl_package_name))
                            if initial_download:
                                return tool_dependency, filtered_actions, dir
                            return tool_dependency, None, None
                        with lcd(tmp_work_dir):
                            cmd = install_environment.build_command(basic_util.evaluate_template(cmd, install_environment))
                            return_code = install_environment.handle_command(tool_dependency=tool_dependency,
                                                                             cmd=cmd,
                                                                             return_output=False,
                                                                             job_name=package_name)
                            if return_code:
                                if initial_download:
                                    return tool_dependency, filtered_actions, dir
                                return tool_dependency, None, None
                    else:
                        # perl package from CPAN without version number.
                        # cpanm should be installed with the parent perl distribution, otherwise this will not work.
                        cmd += '''cpanm --local-lib=$INSTALL_DIR %s''' % (perl_package)
                        cmd = install_environment.build_command(basic_util.evaluate_template(cmd, install_environment))
                        return_code = install_environment.handle_command(tool_dependency=tool_dependency,
                                                                         cmd=cmd,
                                                                         return_output=False,
                                                                         job_name=package_name)
                        if return_code:
                            if initial_download:
                                return tool_dependency, filtered_actions, dir
                            return tool_dependency, None, None
                # Pull in perl dependencies (runtime).
                env_file_builder.handle_action_shell_file_paths(action_dict)
                # Recursively add dependent PERL5LIB and PATH to env.sh & anything else needed.
                env_file_builder.append_line(name="PERL5LIB",
                                             action="prepend_to",
                                             value=os.path.join(install_environment.install_dir, 'lib', 'perl5'))
                env_file_builder.append_line(name="PATH",
                                             action="prepend_to",
                                             value=os.path.join(install_environment.install_dir, 'bin'))
                return_code = env_file_builder.return_code
                if return_code:
                    if initial_download:
                        return tool_dependency, filtered_actions, dir
                    return tool_dependency, None, None
        if initial_download:
            return tool_dependency, filtered_actions, dir
        return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # setup a Perl environment.
        # <action type="setup_perl_environment">
        #       <repository name="package_perl_5_18" owner="bgruening">
        #           <package name="perl" version="5.18.1" />
        #       </repository>
        #       <!-- allow downloading and installing an Perl package from cpan.org-->
        #       <package>XML::Parser</package>
        #       <package>http://search.cpan.org/CPAN/authors/id/C/CJ/CJFIELDS/BioPerl-1.6.922.tar.gz</package>
        # </action>
        # Discover all child repository dependency tags and define the path to an env.sh file associated
        # with each repository.  This will potentially update the value of the 'env_shell_file_paths' entry
        # in action_dict.
        all_env_shell_file_paths = []
        env_manager = EnvManager(self.app)
        action_dict = env_manager.get_env_shell_file_paths_from_setup_environment_elem(all_env_shell_file_paths,
                                                                                       action_elem,
                                                                                       action_dict)
        perl_packages = []
        for env_elem in action_elem:
            if env_elem.tag == 'package':
                # A valid package definition can be:
                #    XML::Parser
                #     http://search.cpan.org/CPAN/authors/id/C/CJ/CJFIELDS/BioPerl-1.6.922.tar.gz
                # Unfortunately CPAN does not support versioning, so if you want real reproducibility you need to specify
                # the tarball path and the right order of different tarballs manually.
                perl_packages.append(dict(package=env_elem.text.strip(),
                                          checksums=self.get_elem_checksums(env_elem)))
        if perl_packages:
            action_dict['perl_packages'] = perl_packages
        return action_dict


class SetupREnvironment(Download, RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'setup_r_environment'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Initialize the environment for installing R packages.  The class is called during the initial
        download stage when installing packages, so the value of initial_download will generally be True.
        However, the parameter value allows this class to also be used in the second stage of the installation,
        although it may never be necessary.  If initial_download is True, the recipe steps will be filtered
        and returned and the installation directory (i.e., dir) will be defined and returned.  If we're not
        in the initial download stage, these actions will not occur, and None values will be returned for them.
        """
        # <action type="setup_r_environment">
        #       <repository name="package_r_3_0_1" owner="bgruening">
        #           <package name="R" version="3.0.1" />
        #       </repository>
        #       <!-- allow installing one or more R packages -->
        #       <package sha256sum="7056b06041fd96ebea9c74f445906f1a5cd784b2b1573c02fcaee86a40f3034d">https://github.com/bgruening/download_store/raw/master/DESeq2-1_0_18/BiocGenerics_0.6.0.tar.gz</package>
        # </action>
        dir = None
        if initial_download:
            filtered_actions = actions[1:]
        env_shell_file_paths = action_dict.get('env_shell_file_paths', None)
        if env_shell_file_paths is None:
            error_message = 'Missing R environment. Please check your specified R installation exists.'
            log.error(error_message)
            status = self.app.install_model.ToolDependency.installation_status.ERROR
            tool_dependency = tool_dependency_util.set_tool_dependency_attributes(self.app,
                                                                                  tool_dependency,
                                                                                  status=status,
                                                                                  error_message=error_message)
            return tool_dependency, [], None
        else:
            install_environment.add_env_shell_file_paths(env_shell_file_paths)
        log.debug('Handling setup_r_environment for tool dependency %s with install_environment.env_shell_file_paths:\n%s' %
                  (str(tool_dependency.name), str(install_environment.env_shell_file_paths)))
        tarball_names = []
        for r_package_dict in action_dict['r_packages']:
            url = r_package_dict['package']
            filename = url.split('/')[-1]
            tarball_names.append(filename)
            checksums = r_package_dict.get('checksums', {})
            self.url_download(work_dir, filename, url, extract=False, checksums=checksums)
        dir = os.path.curdir
        current_dir = os.path.abspath(os.path.join(work_dir, dir))
        with lcd(current_dir):
            with settings(warn_only=True):
                for tarball_name in tarball_names:
                    # Use raw strings so that python won't automatically unescape the quotes before passing the command
                    # to subprocess.Popen.
                    cmd = r'''PATH=$PATH:$R_HOME/bin; export PATH; R_LIBS=$INSTALL_DIR:$R_LIBS; export R_LIBS;
                        Rscript -e "tryCatch( { install.packages(c('%s'), lib = '$INSTALL_DIR', repos = NULL, dependencies = FALSE) }, error = function(e) { print(e); quit(status = 1) }, warning = function(w) { if ( grepl('had non-zero exit status|is not writable|installation of one of more packages failed', as.character(w)) ) { print(w); quit(status = 1) } } )"''' % \
                        (str(tarball_name))
                    cmd = install_environment.build_command(basic_util.evaluate_template(cmd, install_environment))
                    return_code = install_environment.handle_command(tool_dependency=tool_dependency,
                                                                     cmd=cmd,
                                                                     return_output=False,
                                                                     job_name=package_name)
                    if return_code:
                        if initial_download:
                            return tool_dependency, filtered_actions, dir
                        return tool_dependency, None, None
                # R libraries are installed to $INSTALL_DIR (install_dir), we now set the R_LIBS path to that directory
                # Pull in R environment (runtime).
                env_file_builder.handle_action_shell_file_paths(action_dict)
                env_file_builder.append_line(name="R_LIBS", action="prepend_to", value=install_environment.install_dir)
                return_code = env_file_builder.return_code
                if return_code:
                    if initial_download:
                        return tool_dependency, filtered_actions, dir
                    return tool_dependency, None, None
        if initial_download:
            return tool_dependency, filtered_actions, dir
        return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # setup an R environment.
        # <action type="setup_r_environment">
        #       <repository name="package_r_3_0_1" owner="bgruening">
        #           <package name="R" version="3.0.1" />
        #       </repository>
        #       <!-- allow installing an R packages -->
        #       <package>https://github.com/bgruening/download_store/raw/master/DESeq2-1_0_18/BiocGenerics_0.6.0.tar.gz</package>
        # </action>
        # Discover all child repository dependency tags and define the path to an env.sh file
        # associated with each repository.  This will potentially update the value of the
        # 'env_shell_file_paths' entry in action_dict.
        all_env_shell_file_paths = []
        env_manager = EnvManager(self.app)
        action_dict = env_manager.get_env_shell_file_paths_from_setup_environment_elem(all_env_shell_file_paths,
                                                                                       action_elem,
                                                                                       action_dict)
        r_packages = list()
        for env_elem in action_elem:
            if env_elem.tag == 'package':
                r_packages.append(dict(package=env_elem.text.strip(),
                                       checksums=self.get_elem_checksums(env_elem)))
        if r_packages:
            action_dict['r_packages'] = r_packages
        return action_dict


class SetupRubyEnvironment(Download, RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'setup_ruby_environment'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Initialize the environment for installing Ruby packages.  The class is called during the initial
        download stage when installing packages, so the value of initial_download will generally be True.
        However, the parameter value allows this class to also be used in the second stage of the installation,
        although it may never be necessary.  If initial_download is True, the recipe steps will be filtered
        and returned and the installation directory (i.e., dir) will be defined and returned.  If we're not
        in the initial download stage, these actions will not occur, and None values will be returned for them.
        """
        # <action type="setup_ruby_environment">
        #       <repository name="package_ruby_2_0" owner="bgruening">
        #           <package name="ruby" version="2.0" />
        #       </repository>
        #       <!-- allow downloading and installing an Ruby package from http://rubygems.org/ -->
        #       <package>protk</package>
        #       <package>protk=1.2.4</package>
        #       <package>http://url-to-some-gem-file.de/protk.gem</package>
        # </action>
        dir = None
        if initial_download:
            filtered_actions = actions[1:]
        env_shell_file_paths = action_dict.get('env_shell_file_paths', None)
        if env_shell_file_paths is None:
            log.debug('Missing Ruby environment, make sure your specified Ruby installation exists.')
            if initial_download:
                return tool_dependency, filtered_actions, dir
            return tool_dependency, None, None
        else:
            install_environment.add_env_shell_file_paths(env_shell_file_paths)
        log.debug('Handling setup_ruby_environment for tool dependency %s with install_environment.env_shell_file_paths:\n%s' %
                  (str(tool_dependency.name), str(install_environment.env_shell_file_paths)))
        dir = os.path.curdir
        current_dir = os.path.abspath(os.path.join(work_dir, dir))
        with lcd(current_dir):
            with settings(warn_only=True):
                ruby_package_tups = action_dict.get('ruby_package_tups', [])
                for ruby_package_tup_dict in ruby_package_tups:
                    ruby_package_tup = ruby_package_tup_dict['package']
                    gem, gem_version, gem_parameters = ruby_package_tup
                    if gem_parameters:
                        gem_parameters = '-- %s' % gem_parameters
                    else:
                        gem_parameters = ''
                    if os.path.isfile(gem):
                        # we assume a local shipped gem file
                        cmd = '''PATH=$PATH:$RUBY_HOME/bin; export PATH; GEM_HOME=$INSTALL_DIR; export GEM_HOME;
                                gem install --local %s %s''' % (gem, gem_parameters)
                    elif gem.find('://') != -1:
                        # We assume a URL to a gem file.
                        url = gem
                        gem_name = url.split('/')[-1]
                        checksums = ruby_package_tup_dict.get('checksums', {})
                        self.url_download(work_dir, gem_name, url, extract=False, checksums=checksums)
                        cmd = '''PATH=$PATH:$RUBY_HOME/bin; export PATH; GEM_HOME=$INSTALL_DIR; export GEM_HOME;
                                gem install --local %s %s''' % (gem_name, gem_parameters)
                    else:
                        # gem file from rubygems.org with or without version number
                        if gem_version:
                            # Specific ruby gem version was requested.
                            # Use raw strings so that python won't automatically unescape the quotes before passing the command
                            # to subprocess.Popen.
                            cmd = r'''PATH=$PATH:$RUBY_HOME/bin; export PATH; GEM_HOME=$INSTALL_DIR; export GEM_HOME;
                                gem install %s --version "=%s" %s''' % (gem, gem_version, gem_parameters)
                        else:
                            # no version number given
                            cmd = '''PATH=$PATH:$RUBY_HOME/bin; export PATH; GEM_HOME=$INSTALL_DIR; export GEM_HOME;
                                gem install %s %s''' % (gem, gem_parameters)
                    cmd = install_environment.build_command(basic_util.evaluate_template(cmd, install_environment))
                    return_code = install_environment.handle_command(tool_dependency=tool_dependency,
                                                                     cmd=cmd,
                                                                     return_output=False,
                                                                     job_name=package_name)
                    if return_code:
                        if initial_download:
                            return tool_dependency, filtered_actions, dir
                        return tool_dependency, None, None
                # Pull in ruby dependencies (runtime).
                env_file_builder.handle_action_shell_file_paths(action_dict)
                env_file_builder.append_line(name="GEM_PATH",
                                             action="prepend_to",
                                             value=install_environment.install_dir)
                env_file_builder.append_line(name="PATH",
                                             action="prepend_to",
                                             value=os.path.join(install_environment.install_dir, 'bin'))
                return_code = env_file_builder.return_code
                if return_code:
                    if initial_download:
                        return tool_dependency, filtered_actions, dir
                    return tool_dependency, None, None
        if initial_download:
            return tool_dependency, filtered_actions, dir
        return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # setup a Ruby environment.
        # <action type="setup_ruby_environment">
        #       <repository name="package_ruby_2_0" owner="bgruening">
        #           <package name="ruby" version="2.0" />
        #       </repository>
        #       <!-- allow downloading and installing an Ruby package from http://rubygems.org/ -->
        #       <package>protk</package>
        #       <package>protk=1.2.4</package>
        #       <package sha256sum="some_hash">http://url-to-some-gem-file.de/protk.gem</package>
        # </action>
        # Discover all child repository dependency tags and define the path to an env.sh file
        # associated with each repository.  This will potentially update the value of the
        # 'env_shell_file_paths' entry in action_dict.
        all_env_shell_file_paths = []
        env_manager = EnvManager(self.app)
        action_dict = env_manager.get_env_shell_file_paths_from_setup_environment_elem(all_env_shell_file_paths,
                                                                                       action_elem,
                                                                                       action_dict)
        ruby_package_tups = []
        for env_elem in action_elem:
            if env_elem.tag == 'package':
                # A valid gem definition can be:
                #    protk=1.2.4
                #    protk
                #    ftp://ftp.gruening.de/protk.gem
                gem_token = env_elem.text.strip().split('=')
                gem_parameters = env_elem.get('parameters', None)
                if len(gem_token) == 2:
                    # version string
                    gem_name = gem_token[0]
                    gem_version = gem_token[1]
                    tup = (gem_name, gem_version, gem_parameters)
                else:
                    # gem name for rubygems.org without version number
                    gem = env_elem.text.strip()
                    tup = (gem, None, gem_parameters)
                ruby_package_tups.append(dict(package=tup,
                                              checksums=self.get_elem_checksums(env_elem)))
        if ruby_package_tups:
            action_dict['ruby_package_tups'] = ruby_package_tups
        return action_dict


class SetupPythonEnvironment(Download, RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'setup_python_environment'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Initialize the environment for installing Python packages.  The class is called during the initial
        download stage when installing packages, so the value of initial_download will generally be True.
        However, the parameter value allows this class to also be used in the second stage of the installation,
        although it may never be necessary.  If initial_download is True, the recipe steps will be filtered
        and returned and the installation directory (i.e., dir) will be defined and returned.  If we're not
        in the initial download stage, these actions will not occur, and None values will be returned for them.
        """
        # <action type="setup_python_environment">
        #       <repository name="package_python_2_7" owner="bgruening">
        #           <package name="python" version="2.7" />
        #       </repository>
        #       <!-- allow downloading and installing a Python package from https://pypi.python.org/ -->
        #       <package>pysam.tar.gz</package>
        #       <package sha256sum="some_hash">http://url-to-some-python-package.de/pysam.tar.gz</package>
        # </action>
        dir = None
        if initial_download:
            filtered_actions = actions[1:]
        env_shell_file_paths = action_dict.get('env_shell_file_paths', None)
        if env_shell_file_paths is None:
            log.debug('Missing Python environment, make sure your specified Python installation exists.')
            if initial_download:
                return tool_dependency, filtered_actions, dir
            return tool_dependency, None, None
        else:
            install_environment.add_env_shell_file_paths(env_shell_file_paths)
        log.debug('Handling setup_python_environment for tool dependency %s with install_environment.env_shell_file_paths:\n%s' %
                  (str(tool_dependency.name), str(install_environment.env_shell_file_paths)))
        dir = os.path.curdir
        current_dir = os.path.abspath(os.path.join(work_dir, dir))
        with lcd(current_dir):
            with settings(warn_only=True):
                python_package_tups = action_dict.get('python_package_tups', [])
                for python_package_tup_dict in python_package_tups:
                    python_package_tup = python_package_tup_dict['package']
                    package, package_version = python_package_tup
                    package_path = os.path.join(install_environment.tool_shed_repository_install_dir, package)
                    if os.path.isfile(package_path):
                        # We assume a local shipped python package.
                        package_to_install = package_path
                    elif package.find('://') != -1:
                        # We assume a URL to a python package.
                        url = package
                        package_name = url.split('/')[-1]
                        checksums = python_package_tup_dict.get('checksums', {})
                        self.url_download(work_dir, package_name, url, extract=False, checksums=checksums)
                        package_to_install = os.path.join(work_dir, package_name)
                    else:
                        # pypi support is currently not working - pip can not install wheels into user specified directories
                        pass
                    archive = CompressedFile(package_to_install)
                    uncompressed_path = archive.extract(work_dir)
                    cmd = r'''PATH=$PYTHONHOME/bin:$PATH; export PATH;
                            mkdir -p $INSTALL_DIR/lib/python;
                            export PYTHONPATH=$INSTALL_DIR/lib/python:$PYTHONPATH;
                            cd %s;
                            python setup.py install --install-lib $INSTALL_DIR/lib/python --install-scripts $INSTALL_DIR/bin
                        ''' % (uncompressed_path)

                    cmd = install_environment.build_command(basic_util.evaluate_template(cmd, install_environment))
                    return_code = install_environment.handle_command(tool_dependency=tool_dependency,
                                                                     cmd=cmd,
                                                                     return_output=False,
                                                                     job_name=package_name)
                    if return_code:
                        if initial_download:
                            return tool_dependency, filtered_actions, dir
                        return tool_dependency, None, None
                # Pull in python dependencies (runtime).
                env_file_builder.handle_action_shell_file_paths(action_dict)
                env_file_builder.append_line(name="PYTHONPATH",
                                             action="prepend_to",
                                             value=os.path.join(install_environment.install_dir, 'lib', 'python'))
                env_file_builder.append_line(name="PYTHONPATH",
                                             action="prepend_to",
                                             value=os.path.join(install_environment.install_dir))
                env_file_builder.append_line(name="PATH",
                                             action="prepend_to",
                                             value=os.path.join(install_environment.install_dir, 'bin'))
                return_code = env_file_builder.return_code
                if return_code:
                    if initial_download:
                        return tool_dependency, filtered_actions, dir
                    return tool_dependency, None, None
        if initial_download:
            return tool_dependency, filtered_actions, dir
        return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # setup a Python environment.
        # <action type="setup_python_environment">
        #       <repository name="package_python_2_7" owner="bgruening">
        #           <package name="python" version="2.7" />
        #       </repository>
        #       <!-- allow downloading and installing an Python package from https://pypi.org/ -->
        #       <package>pysam.tar.gz</package>
        #       <package>http://url-to-some-python-package.de/pysam.tar.gz</package>
        # </action>
        # Discover all child repository dependency tags and define the path to an env.sh file
        # associated with each repository.  This will potentially update the value of the
        # 'env_shell_file_paths' entry in action_dict.
        all_env_shell_file_paths = []
        env_manager = EnvManager(self.app)
        action_dict = env_manager.get_env_shell_file_paths_from_setup_environment_elem(all_env_shell_file_paths,
                                                                                       action_elem,
                                                                                       action_dict)
        python_package_tups = []
        for env_elem in action_elem:
            if env_elem.tag == 'package':
                # A valid package definitions can be:
                #    pysam.tar.gz -> locally shipped tarball
                #    ftp://ftp.gruening.de/pysam.tar.gz -> online tarball
                python_token = env_elem.text.strip().split('=')
                if len(python_token) == 2:
                    # version string
                    package_name = python_token[0]
                    package_version = python_token[1]
                    tup = (package_name, package_version)
                else:
                    # package name for pypi.org without version number
                    package = env_elem.text.strip()
                    tup = (package, None)
                python_package_tups.append(dict(package=tup,
                                                checksums=self.get_elem_checksums(env_elem)))
        if python_package_tups:
            action_dict['python_package_tups'] = python_package_tups
        action_dict.update(self.get_elem_checksums(action_elem))
        return action_dict


class SetupVirtualEnv(Download, RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'setup_virtualenv'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Initialize a virtual environment for installing packages.  If initial_download is True, the recipe
        steps will be filtered and returned and the installation directory (i.e., dir) will be defined and
        returned.  If we're not in the initial download stage, these actions will not occur, and None values
        will be returned for them.
        """
        # This class is not currently used during stage 1 of the installation process, so filter_actions
        # are not affected, and dir is not set.  Enhancements can easily be made to this function if this
        # class is needed in stage 1.
        venv_src_directory = os.path.abspath(os.path.join(self.app.config.tool_dependency_dir, '__virtualenv_src'))
        if not self.install_virtualenv(install_environment, venv_src_directory):
            log.debug('Unable to install virtualenv')
            return tool_dependency, None, None
        requirements = action_dict['requirements']
        if os.path.exists(os.path.join(install_environment.install_dir, requirements)):
            # requirements specified as path to a file
            requirements_path = requirements
        else:
            # requirements specified directly in XML, create a file with these for pip.
            requirements_path = os.path.join(install_environment.install_dir, "requirements.txt")
            with open(requirements_path, "w") as f:
                f.write(requirements)
        venv_directory = os.path.join(install_environment.install_dir, "venv")
        python_cmd = action_dict['python']
        # TODO: Consider making --no-site-packages optional.
        setup_command = "%s %s/virtualenv.py --no-site-packages '%s'" % (python_cmd, venv_src_directory, venv_directory)
        # POSIXLY_CORRECT forces shell commands . and source to have the same
        # and well defined behavior in bash/zsh.
        activate_command = "POSIXLY_CORRECT=1; . %s" % os.path.join(venv_directory, "bin", "activate")
        if action_dict['use_requirements_file']:
            install_command = "python '%s' install -r '%s' --log '%s'" % \
                (os.path.join(venv_directory, "bin", "pip"),
                 requirements_path,
                 os.path.join(install_environment.install_dir, 'pip_install.log'))
        else:
            install_command = ''
            with open(requirements_path, "rb") as f:
                while True:
                    line = f.readline()
                    if not line:
                        break
                    line = line.strip()
                    if line:
                        line_install_command = "python '%s' install %s --log '%s'" % \
                            (os.path.join(venv_directory, "bin", "pip"),
                             line,
                             os.path.join(install_environment.install_dir, 'pip_install_%s.log' % (line)))
                        if not install_command:
                            install_command = line_install_command
                        else:
                            install_command = "%s && %s" % (install_command, line_install_command)
        full_setup_command = "%s; %s; %s" % (setup_command, activate_command, install_command)
        return_code = install_environment.handle_command(tool_dependency=tool_dependency,
                                                         cmd=full_setup_command,
                                                         return_output=False,
                                                         job_name=package_name)
        if return_code:
            log.error("Failed to do setup_virtualenv install, exit code='%s'", return_code)
            # would it be better to try to set env variables anway, instead of returning here?
            return tool_dependency, None, None
        site_packages_directory, site_packages_directory_list = \
            self.__get_site_packages_directory(install_environment,
                                               self.app,
                                               tool_dependency,
                                               python_cmd,
                                               venv_directory)
        env_file_builder.append_line(name="PATH", action="prepend_to", value=os.path.join(venv_directory, "bin"))
        if site_packages_directory is None:
            log.error("virtualenv's site-packages directory '%s' does not exist", site_packages_directory_list)
        else:
            env_file_builder.append_line(name="PYTHONPATH", action="prepend_to", value=site_packages_directory)
        # The caller should check the status of the returned tool_dependency since this function does nothing
        # with the return_code.
        return_code = env_file_builder.return_code
        return tool_dependency, None, None

    def install_virtualenv(self, install_environment, venv_dir):
        if not os.path.exists(venv_dir):
            with install_environment.use_tmp_dir() as work_dir:
                downloaded_filename = VIRTUALENV_URL.rsplit('/', 1)[-1]
                try:
                    dir = self.url_download(work_dir, downloaded_filename, VIRTUALENV_URL)
                except Exception:
                    log.error("Failed to download virtualenv: url_download( '%s', '%s', '%s' ) threw an exception",
                              work_dir, downloaded_filename, VIRTUALENV_URL)
                    return False
                full_path_to_dir = os.path.abspath(os.path.join(work_dir, dir))
                shutil.move(full_path_to_dir, venv_dir)
        return True

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # <action type="setup_virtualenv" />
        # Install requirements from file requirements.txt of downloaded bundle - or -
        # <action type="setup_virtualenv">tools/requirements.txt</action>
        # Install requirements from specified file from downloaded bundle -or -
        # <action type="setup_virtualenv">pyyaml==3.2.0
        # lxml==2.3.0</action>
        # Manually specify contents of requirements.txt file to create dynamically.
        action_dict['use_requirements_file'] = asbool(action_elem.get('use_requirements_file', True))
        action_dict['requirements'] = basic_util.evaluate_template(action_elem.text or 'requirements.txt', install_environment)
        action_dict['python'] = action_elem.get('python', 'python')
        return action_dict

    def __get_site_packages_directory(self, install_environment, app, tool_dependency, python_cmd, venv_directory):
        lib_dir = os.path.join(venv_directory, "lib")
        rval = os.path.join(lib_dir, python_cmd, 'site-packages')
        site_packages_directory_list = [rval]
        if os.path.exists(rval):
            return (rval, site_packages_directory_list)
        for (dirpath, dirnames, filenames) in os.walk(lib_dir):
            for dirname in dirnames:
                rval = os.path.join(lib_dir, dirname, 'site-packages')
                site_packages_directory_list.append(rval)
                if os.path.exists(rval):
                    return (rval, site_packages_directory_list)
            break
        # fall back to python call to get site packages
        # FIXME: This is probably more robust?, but there is currently an issue with handling the output.stdout
        # preventing the entire path from being included (it gets truncated)
        # Use raw strings so that python won't automatically unescape the quotes before passing the command
        # to subprocess.Popen.
        for site_packages_command in [r"""%s -c 'import site; site.getsitepackages()[0]'""" %
                                      os.path.join(venv_directory, "bin", "python"),
                                      r"""%s -c 'from __future__ import print_function; import os, sys; print(os.path.join(sys.prefix, "lib", "python" + sys.version[:3], "site-packages"))'""" %
                                      os.path.join(venv_directory, "bin", "python")]:
            output = install_environment.handle_command(tool_dependency=tool_dependency,
                                                        cmd=site_packages_command,
                                                        return_output=True,
                                                        job_name='_get_site_packages')
            site_packages_directory_list.append(output.stdout)
            if not output.return_code and os.path.exists(output.stdout):
                return (output.stdout, site_packages_directory_list)
        return (None, site_packages_directory_list)


class ShellCommand(RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'shell_command'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Execute a command in a shell.  If the value of initial_download is True, the recipe steps will
        be filtered and returned and the installation directory (i.e., dir) will be defined and returned.
        If we're not in the initial download stage, these actions will not occur, and None values will
        be returned for them.
        """
        # <action type="shell_command">git clone --recursive git://github.com/ekg/freebayes.git</action>
        # Eliminate the shell_command clone action so remaining actions can be processed correctly.
        if initial_download:
            # I'm not sure why we build the cmd differently in stage 1 vs stage 2.  Should this process
            # be the same no matter the stage?
            dir = package_name
            filtered_actions = actions[1:]
            cmd = action_dict['command']
        else:
            cmd = install_environment.build_command(action_dict['command'])
        with settings(warn_only=True):
            # The caller should check the status of the returned tool_dependency since this function
            # does nothing with return_code.
            install_environment.handle_command(tool_dependency=tool_dependency,
                                               cmd=cmd,
                                               return_output=False,
                                               job_name=package_name)
            if initial_download:
                return tool_dependency, filtered_actions, dir
            return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # <action type="shell_command">make</action>
        action_elem_text = basic_util.evaluate_template(action_elem.text, install_environment)
        if action_elem_text:
            action_dict['command'] = action_elem_text
        return action_dict


class TemplateCommand(RecipeStep):

    def __init__(self, app):
        self.app = app
        self.type = 'template_command'

    def execute_step(self, tool_dependency, package_name, actions, action_dict, filtered_actions, env_file_builder,
                     install_environment, work_dir, current_dir=None, initial_download=False):
        """
        Execute a template command in a shell.  If the value of initial_download is True, the recipe steps
        will be filtered and returned and the installation directory (i.e., dir) will be defined and returned.
        If we're not in the initial download stage, these actions will not occur, and None values will be
        returned for them.
        """
        env_vars = dict()
        env_vars = install_environment.environment_dict()
        env_vars.update(basic_util.get_env_var_values(install_environment))
        language = action_dict['language']
        with settings(warn_only=True, **env_vars):
            if language == 'cheetah':
                # We need to import fabric.api.env so that we can access all collected environment variables.
                cmd = fill_template('#from fabric.api import env\n%s' % action_dict['command'], context=env_vars)
                # The caller should check the status of the returned tool_dependency since this function
                # does nothing with return_code.
                install_environment.handle_command(tool_dependency=tool_dependency,
                                                   cmd=cmd,
                                                   return_output=False,
                                                   job_name=package_name)
            return tool_dependency, None, None

    def prepare_step(self, tool_dependency, action_elem, action_dict, install_environment, is_binary_download):
        # Default to Cheetah as it's the first template language supported.
        language = action_elem.get('language', 'cheetah').lower()
        if language == 'cheetah':
            # Cheetah template syntax.
            # <action type="template_command" language="cheetah">
            #     #if env.PATH:
            #         make
            #     #end if
            # </action>
            action_elem_text = action_elem.text.strip()
            if action_elem_text:
                action_dict['language'] = language
                action_dict['command'] = action_elem_text
        else:
            log.debug("Unsupported template language '%s'. Not proceeding." % str(language))
            raise Exception("Unsupported template language '%s' in tool dependency definition." % str(language))
        return action_dict
