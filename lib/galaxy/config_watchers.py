from functools import partial
from os.path import dirname

from galaxy.config import reload_config_options
from galaxy.queue_worker import job_rule_modules
from galaxy.tools.toolbox.watcher import (
    get_tool_conf_watcher,
    get_tool_watcher,
)
from galaxy.util.watcher import get_watcher


class ConfigWatchers(object):
    """Contains ToolConfWatcher, ToolWatcher and ToolDataWatcher objects."""

    def __init__(self, app):
        self.app = app
        self.active = False
        # ToolConfWatcher objects will watch the tool_cache if the tool_cache is passed into get_tool_conf_watcher.
        # Watching the tool_cache means removing outdated items from the tool_cache.
        # Only the reload_toolbox callback will re-populate the cache, so we pass the tool_cache only to the ToolConfWatcher that
        # watches regular tools.
        # If there are multiple ToolConfWatcher objects for the same handler or web process a race condition occurs between the two cache_cleanup functions.
        # If the reload_data_managers callback wins, the cache will miss the tools that had been removed from the cache
        # and will be blind to further changes in these tools.
        self.tool_config_watcher = get_tool_conf_watcher(
            reload_callback=lambda: self.app.queue_worker.send_control_task('reload_toolbox'),
            tool_cache=self.app.tool_cache,
        )
        self.data_manager_config_watcher = get_tool_conf_watcher(
            reload_callback=lambda: self.app.queue_worker.send_control_task('reload_data_managers'),
        )
        self.tool_data_watcher = get_watcher(self.app.config, 'watch_tool_data_dir', monitor_what_str='data tables')
        self.tool_watcher = get_tool_watcher(self, app.config)
        if getattr(self.app, 'is_job_handler', False):
            self.job_rule_watcher = get_watcher(app.config, 'watch_job_rules', monitor_what_str='job rules')
        else:
            self.job_rule_watcher = get_watcher(app.config, '__invalid__')
        self.core_config_watcher = get_watcher(
            app.config,
            'watch_core_config',
            monitor_what_str='core config file'
        )

    @property
    def watchers(self):
        return (self.tool_watcher,
                self.tool_config_watcher,
                self.data_manager_config_watcher,
                self.tool_data_watcher,
                self.tool_watcher,
                self.job_rule_watcher,
                self.core_config_watcher)

    def change_state(self, active):
        if active:
            self.start()
        elif self.active:
            self.shutdown()

    def start(self):
        for watcher in self.watchers:
            watcher.start()
        [self.tool_config_watcher.watch_file(config) for config in self.tool_config_paths]
        [self.data_manager_config_watcher.watch_file(config) for config in self.data_manager_configs]
        for tool_data_path in self.tool_data_paths:
            self.tool_data_watcher.watch_directory(
                tool_data_path,
                callback=lambda path: self.app.queue_worker.send_control_task('reload_tool_data_tables', kwargs={'path': path}),
                require_extensions=('.loc',),
                recursive=True,
            )
        for job_rules_directory in self.job_rules_paths:
            self.job_rule_watcher.watch_directory(
                job_rules_directory,
                callback=lambda: self.app.queue_worker.send_control_task('reload_job_rules'),
                recursive=True,
                ignore_extensions=('.pyc', '.pyo', '.pyd'))
        if self.app.config.config_file:
            self.core_config_watcher.watch_file(
                self.app.config.config_file,
                callback=partial(reload_config_options, self.app.config)
            )
        self.active = True

    def shutdown(self):
        for watcher in self.watchers:
            watcher.shutdown()
        self.active = False

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
        return tool_config_paths

    @property
    def job_rules_paths(self):
        job_rules_paths = []
        for rules_module in job_rule_modules(self.app):
            job_rules_dir = dirname(rules_module.__file__)
            job_rules_paths.append(job_rules_dir)
        return job_rules_paths
