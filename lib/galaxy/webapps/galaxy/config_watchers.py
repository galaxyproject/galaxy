from functools import partial
from os.path import dirname

from galaxy.queue_worker import (
    job_rule_modules,
    reload_data_managers,
    reload_job_rules,
    reload_toolbox
)
from galaxy.tools.toolbox.watcher import (
    get_tool_conf_watcher,
    get_tool_data_dir_watcher,
    get_tool_watcher,
)
from galaxy.util.watcher import (
    get_watcher,
)


class ConfigWatchers(object):
    """Contains ToolConfWatcher, ToolWatcher and ToolDataWatcher objects."""

    def __init__(self, app):
        self.app = app
        # ToolConfWatcher objects will watch the tool_cache if the tool_cache is passed into get_tool_conf_watcher.
        # Watching the tool_cache means removing outdated items from the tool_cache.
        # Only the reload_toolbox callback will re-populate the cache, so we pass the tool_cache only to the ToolConfWatcher that
        # watches regular tools.
        # If there are multiple ToolConfWatcher objects for the same handler or web process a race condition occurs between the two cache_cleanup functions.
        # If the reload_data_managers callback wins, the cache will miss the tools that had been removed from the cache
        # and will be blind to further changes in these tools.
        self.tool_config_watcher = get_tool_conf_watcher(reload_callback=lambda: reload_toolbox(self.app), tool_cache=self.app.tool_cache)
        self.data_manager_config_watcher = get_tool_conf_watcher(reload_callback=lambda: reload_data_managers(self.app))
        self.tool_data_watcher = get_tool_data_dir_watcher(self.app.tool_data_tables, config=self.app.config)
        self.tool_watcher = get_tool_watcher(self, app.config)
        if getattr(self.app, 'is_job_handler', False):
            self.job_rule_watcher = get_watcher(app.config, 'watch_job_rules', monitor_what_str='job rules')
        else:
            self.job_rule_watcher = get_watcher(app.config, '__invalid__')
        self.start()

    def start(self):
        [self.tool_config_watcher.watch_file(config) for config in self.tool_config_paths]
        [self.data_manager_config_watcher.watch_file(config) for config in self.data_manager_configs]
        [self.tool_data_watcher.watch_directory(tool_data_path) for tool_data_path in self.tool_data_paths]
        for job_rules_directory in self.job_rules_paths:
            self.job_rule_watcher.watch_directory(
                job_rules_directory,
                callback=partial(reload_job_rules, self.app),
                recursive=True,
                ignore_extensions=('.pyc', '.pyo', '.pyd'))

    def shutdown(self):
        self.tool_config_watcher.shutdown()
        self.data_manager_config_watcher.shutdown()
        self.tool_data_watcher.shutdown()
        self.tool_watcher.shutdown()

    def update_watch_data_table_paths(self):
        if hasattr(self.tool_data_watcher, 'monitored_dirs'):
            for tool_data_table_path in self.tool_data_paths:
                if tool_data_table_path not in self.tool_data_watcher.monitored_dirs:
                    self.tool_data_watcher.watch_directory(tool_data_table_path)

    @property
    def data_manager_configs(self):
        data_manager_configs = []
        if hasattr(self.app.config, 'data_manager_config_file'):
            data_manager_configs.append(self.app.config.data_manager_config_file)
        if hasattr(self.app.config, 'shed_data_manager_config_file'):
            data_manager_configs.append(self.app.config.shed_data_manager_config_file)
        return data_manager_configs

    @property
    def tool_data_paths(self):
        tool_data_paths = []
        if hasattr(self.app.config, 'tool_data_path'):
            tool_data_paths.append(self.app.config.tool_data_path)
        if hasattr(self.app.config, 'shed_tool_data_path'):
            tool_data_paths.append(self.app.config.shed_tool_data_path)
        return tool_data_paths

    @property
    def tool_config_paths(self):
        tool_config_paths = []
        if hasattr(self.app.config, 'tool_configs'):
            tool_config_paths = self.app.config.tool_configs
        if hasattr(self.app.config, 'migrated_tools_config'):
            if self.app.config.migrated_tools_config not in tool_config_paths:
                tool_config_paths.append(self.app.config.migrated_tools_config)
        return tool_config_paths

    @property
    def job_rules_paths(self):
        job_rules_paths = []
        for rules_module in job_rule_modules(self.app):
            job_rules_dir = dirname(rules_module.__file__)
            job_rules_paths.append(job_rules_dir)
        return job_rules_paths
