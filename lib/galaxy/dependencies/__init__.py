"""
Determine what optional dependencies are needed.
"""

import os
import sys
from os.path import (
    dirname,
    exists,
    join,
)

import yaml
from dparse import parse

from galaxy.config import GalaxyAppConfiguration
from galaxy.util import (
    asbool,
    etree,
    parse_xml,
    which,
)
from galaxy.util.properties import (
    find_config_file,
    load_app_properties,
)


class ConditionalDependencies:
    def __init__(self, config_file, config=None):
        self.config_file = config_file
        self.job_runners = []
        self.authenticators = []
        self.object_stores = []
        self.file_sources = []
        self.conditional_reqs = []
        self.container_interface_types = []
        self.job_rule_modules = []
        self.error_report_modules = []
        self.vault_type = None
        if config is None:
            self.config = load_app_properties(config_file=self.config_file)
        else:
            self.config = config
        self.config_object = GalaxyAppConfiguration(config_file=self.config_file, override_tempdir=False, **self.config)
        self.parse_configs()
        self.get_conditional_requirements()

    def parse_configs(self):
        def load_job_config_dict(job_conf_dict):
            runners = job_conf_dict.get("runners", {})
            for runner in runners.values():
                if "load" in runner:
                    self.job_runners.append(runner.get("load"))
            environments = job_conf_dict.get("execution", {}).get("environments", {})
            for env in environments.values():
                if "rules_module" in env:
                    self.job_rule_modules.append(env.get("rules_module"))

        if "job_config" in self.config:
            load_job_config_dict(self.config.get("job_config"))
        else:
            job_conf_path = self.config_object.job_config_file
            if not job_conf_path:
                job_conf_path = join(dirname(self.config_file), "job_conf.yml")
                if not exists(job_conf_path):
                    job_conf_path = join(dirname(self.config_file), "job_conf.xml")
            else:
                job_conf_path = join(dirname(self.config_file), job_conf_path)
            if ".xml" in job_conf_path:
                try:
                    job_conf_tree = parse_xml(job_conf_path)
                    plugins_elem = job_conf_tree.find("plugins")
                    if plugins_elem:
                        for plugin in plugins_elem.findall("plugin"):
                            if "load" in plugin.attrib:
                                self.job_runners.append(plugin.attrib["load"])
                    for plugin in job_conf_tree.findall('.//destination/param[@id="rules_module"]'):
                        self.job_rule_modules.append(plugin.text)
                except (OSError, etree.ParseError):
                    pass
            else:
                try:
                    with open(job_conf_path) as f:
                        job_conf_dict = yaml.safe_load(f)
                    load_job_config_dict(job_conf_dict)
                except OSError:
                    pass

        object_store_conf_path = self.config_object.object_store_config_file
        try:
            if ".xml" in object_store_conf_path:
                for store in parse_xml(object_store_conf_path).iter("object_store"):
                    if "type" in store.attrib:
                        self.object_stores.append(store.attrib["type"])
            else:
                with open(object_store_conf_path) as f:
                    job_conf_dict = yaml.safe_load(f)

                def collect_types(from_dict):
                    if not isinstance(from_dict, dict):
                        return

                    if "type" in from_dict:
                        self.object_stores.append(from_dict["type"])

                    for value in from_dict.values():
                        if isinstance(value, list):
                            for val in value:
                                collect_types(val)
                        else:
                            collect_types(value)

                collect_types(job_conf_dict)

        except OSError:
            pass

        # Parse auth conf
        auth_conf_xml = self.config_object.auth_config_file
        try:
            for auth in parse_xml(auth_conf_xml).findall("authenticator"):
                auth_type = auth.find("type")
                if auth_type is not None:
                    self.authenticators.append(auth_type.text)
        except OSError:
            pass

        # Parse oidc_backends_config_file specifically for PKCE support.
        self.pkce_support = False
        oidc_backend_conf_xml = self.config_object.oidc_backends_config_file
        try:
            for pkce_support_element in parse_xml(oidc_backend_conf_xml).iterfind("./provider/pkce_support"):
                if pkce_support_element.text == "true":
                    self.pkce_support = True
                    break
        except OSError:
            pass

        # Parse error report config
        error_report_yml = self.config_object.error_report_file
        try:
            with open(error_report_yml) as f:
                error_reporters = yaml.safe_load(f)
                self.error_report_modules = [er.get("type", None) for er in error_reporters]
        except OSError:
            pass

        # Parse file sources config
        file_sources_conf_yml = self.config_object.file_sources_config_file

        if exists(file_sources_conf_yml):
            with open(file_sources_conf_yml) as f:
                file_sources_conf = yaml.safe_load(f)
        else:
            file_sources_conf = []
        self.file_sources = [c.get("type", None) for c in file_sources_conf]

        # Parse vault config
        vault_conf_yml = self.config_object.vault_config_file
        if exists(vault_conf_yml):
            with open(vault_conf_yml) as f:
                vault_conf = yaml.safe_load(f)
        else:
            vault_conf = {}
        self.vault_type = vault_conf.get("type", "").lower()

    def get_conditional_requirements(self):
        crfile = join(dirname(__file__), "conditional-requirements.txt")
        with open(crfile) as fh:
            dependency_file = parse(fh.read(), file_type="requirements.txt")
            for dep in dependency_file.dependencies:
                self.conditional_reqs.append(dep)

    def check(self, name):
        try:
            name = name.replace("-", "_").replace(".", "_")
            return getattr(self, f"check_{name}")()
        except Exception:
            return False

    def check_psycopg2_binary(self):
        return self.config["database_connection"].startswith("postgres")

    def check_mysqlclient(self):
        return self.config["database_connection"].startswith("mysql")

    def check_drmaa(self):
        return (
            "galaxy.jobs.runners.drmaa:DRMAAJobRunner" in self.job_runners
            or "galaxy.jobs.runners.slurm:SlurmJobRunner" in self.job_runners
            or "galaxy.jobs.runners.univa:UnivaJobRunner" in self.job_runners
        )

    def check_galaxycloudrunner(self):
        return "galaxycloudrunner.rules" in self.job_rule_modules

    def check_total_perspective_vortex(self):
        return "tpv.rules" in self.job_rule_modules

    def check_pbs_python(self):
        return "galaxy.jobs.runners.pbs:PBSJobRunner" in self.job_runners

    def check_pykube_ng(self):
        return "galaxy.jobs.runners.kubernetes:KubernetesJobRunner" in self.job_runners or which("kubectl")

    def check_chronos_python(self):
        return "galaxy.jobs.runners.chronos:ChronosJobRunner" in self.job_runners

    def check_boto3_python(self):
        return "galaxy.jobs.runners.aws:AWSBatchJobRunner" in self.job_runners

    def check_fluent_logger(self):
        return asbool(self.config["fluent_log"])

    def check_sentry_sdk(self):
        return self.config.get("sentry_dsn", None) is not None

    def check_statsd(self):
        return self.config.get("statsd_host", None) is not None

    def check_python_ldap(self):
        return "ldap" in self.authenticators or "activedirectory" in self.authenticators

    def check_ldap3(self):
        return "ldap3" in self.authenticators

    def check_python_pam(self):
        return "PAM" in self.authenticators

    def check_azure_storage(self):
        return "azure_blob" in self.object_stores

    def check_boto3(self):
        return "boto3" in self.object_stores

    def check_kamaki(self):
        return "pithos" in self.object_stores

    def check_python_irodsclient(self):
        return "irods" in self.object_stores

    def check_fs_dropboxfs(self):
        return "dropbox" in self.file_sources

    def check_fs_webdavfs(self):
        return "webdav" in self.file_sources

    def check_fs_anvilfs(self):
        # pyfilesystem plugin access to terra on anvil
        return "anvil" in self.file_sources

    def check_fs_sshfs(self):
        return "ssh" in self.file_sources

    def check_fs_googledrivefs(self):
        return "googledrive" in self.file_sources

    def check_fs_gcsfs(self):
        return "googlecloudstorage" in self.file_sources

    def check_google_cloud_storage(self):
        return "googlecloudstorage" in self.file_sources

    def check_onedatafilerestclient(self):
        return "onedata" in self.object_stores

    def check_fs_onedatarestfs(self):
        return "onedata" in self.file_sources

    def check_fs_basespace(self):
        return "basespace" in self.file_sources

    def check_watchdog(self):
        install_set = {"auto", "True", "true", "polling", True}
        return self.config["watch_tools"] in install_set or self.config["watch_tool_data_dir"] in install_set

    def check_python_gitlab(self):
        return "gitlab" in self.error_report_modules

    def check_pygithub(self):
        return "github" in self.error_report_modules

    def check_influxdb(self):
        return "influxdb" in self.error_report_modules

    def check_tensorflow(self):
        return asbool(self.config["enable_tool_recommendations"])

    def check_openai(self):
        return self.config.get("openai_api_key", None) is not None

    def check_weasyprint(self):
        # See notes in ./conditional-requirements.txt for more information.
        return os.environ.get("GALAXY_DEPENDENCIES_INSTALL_WEASYPRINT") == "1"

    def check_pydyf(self):
        # See notes in ./conditional-requirements.txt for more information.
        return os.environ.get("GALAXY_DEPENDENCIES_INSTALL_WEASYPRINT") == "1"

    def check_custos_sdk(self):
        return "custos" == self.vault_type

    def check_hvac(self):
        return "hashicorp" == self.vault_type

    def check_pkce(self):
        return self.pkce_support

    def check_rucio_clients(self):
        return "rucio" in self.object_stores and sys.version_info >= (3, 9)


def optional(config_file=None):
    if not config_file:
        config_file = find_config_file(["galaxy", "universe_wsgi"], include_samples=True)
    if not config_file:
        print("galaxy.dependencies.optional: no config file found", file=sys.stderr)
        return []
    rval = []
    conditional = ConditionalDependencies(config_file)
    for dependency in conditional.conditional_reqs:
        if conditional.check(dependency.name):
            rval.append(dependency.line)
    return rval
