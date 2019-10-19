import os
from datetime import timedelta

from base import integration_util


class ConfigDefaultsTestCase(integration_util.IntegrationTestCase):

    def __init__(self, *args, **kwargs):
        super(ConfigDefaultsTestCase, self).__init__(*args, **kwargs)
        # use lazy loading for attributes below
        self._root_dir = None
        self._config_dir = None
        self._mutable_config_dir = None
        self._data_dir = None
        self._tool_data_path = None

    def get_default(self, key):
        # Returns default value or None (because if default value is not
        # specified in the schema, we expect None  by default)
        return self._app.config.appschema[key].get('default', None)

    def get_default_in_config_dir(self, key):
        # Use when schema default is resolved with respect to the value of 'config_dir'
        self._config_dir = self._config_dir or self._app.config.config_dir
        return self._resolve(self._config_dir, self.get_default(key))

    def get_default_in_mutable_config_dir(self, key):
        # Use when schema default is resolved with respect to the value of 'mutable_config_dir'
        self._mutable_config_dir = self._mutable_config_dir or self._app.config.mutable_config_dir
        return self._resolve(self._mutable_config_dir, self.get_default(key))

    def _resolve(self, parent, child):
        return os.path.join(parent, child) if child else parent

    def test_default_shed_tool_config_file(self):
        expect = self.get_default_in_mutable_config_dir('shed_tool_config_file')
        assert expect == self._app.config.shed_tool_config_file
    
    def test_default_dependency_resolvers_config_file(self):
        expect = self.get_default_in_config_dir('dependency_resolvers_config_file')
        assert expect == self._app.config.dependency_resolvers_config_file
    
    def test_default_tool_sheds_config_file(self):
        expect = self.get_default_in_config_dir('tool_sheds_config_file')
        assert expect == self._app.config.tool_sheds_config_file
    
    def test_default_shed_tool_data_table_config(self):
        expect = self.get_default_in_mutable_config_dir('shed_tool_data_table_config')
        assert expect == self._app.config.shed_tool_data_table_config
    
    def test_default_object_store_config_file(self):
        expect = self.get_default_in_config_dir('object_store_config_file')
        assert expect == self._app.config.object_store_config_file
    
    def test_default_user_preferences_extra_conf_path(self):
        expect = self.get_default_in_config_dir('user_preferences_extra_conf_path')
        assert expect == self._app.config.user_preferences_extra_conf_path
    
    def test_default_oidc_config_file(self):
        expect = self.get_default_in_config_dir('oidc_config_file')
        assert expect == self._app.config.oidc_config_file
    
    def test_default_oidc_backends_config_file(self):
        expect = self.get_default_in_config_dir('oidc_backends_config_file')
        assert expect == self._app.config.oidc_backends_config_file
    
    def test_default_auth_config_file(self):
        expect = self.get_default_in_config_dir('auth_config_file')
        assert expect == self._app.config.auth_config_file
    
    def test_default_shed_data_manager_config_file(self):
        expect = self.get_default_in_mutable_config_dir('shed_data_manager_config_file')
        assert expect == self._app.config.shed_data_manager_config_file
    
    def test_default_job_resource_params_file(self):
        expect = self.get_default_in_config_dir('job_resource_params_file')
        assert expect == self._app.config.job_resource_params_file
    
    def test_default_workflow_resource_params_file(self):
        expect = self.get_default_in_config_dir('workflow_resource_params_file')
        assert expect == self._app.config.workflow_resource_params_file
    
    def test_default_workflow_schedulers_config_file(self):
        expect = self.get_default_in_config_dir('workflow_schedulers_config_file')
        assert expect == self._app.config.workflow_schedulers_config_file
