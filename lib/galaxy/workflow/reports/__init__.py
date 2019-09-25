from galaxy.util import plugin_config

DEFAULT_REPORT_GENERATOR_TYPE = "markdown"


def generate_report_json(trans, invocation, runtime_report_config_json=None, plugin_type=None):
    import galaxy.workflow.reports.generators
    plugin_classes = plugin_config.plugins_dict(galaxy.workflow.reports.generators, 'plugin_type')
    plugin_type = plugin_type or DEFAULT_REPORT_GENERATOR_TYPE
    plugin = plugin_classes[plugin_type]()
    return plugin.generate_report_json(trans, invocation, runtime_report_config_json=runtime_report_config_json)
