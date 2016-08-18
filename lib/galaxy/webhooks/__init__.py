"""
This module manages loading of Galaxy webhooks.
"""

import os
import yaml
import logging

from galaxy.util import galaxy_root_path

log = logging.getLogger(__name__)


class WebhooksRegistry(object):
    def __init__(self, webhooks_directories):
        self.webhooks = {}
        path = os.path.join(galaxy_root_path, webhooks_directories)
        self.webhooks_directories = \
            [os.path.join(path, name)
             for name in os.listdir(webhooks_directories)]
        self.load_webhooks()

    def load_webhooks(self):
        for directory in self.webhooks_directories:
            config_dir = os.path.join(directory, 'config')

            if not os.path.exists(config_dir):
                log.warning('directory not found: %s', config_dir)
                continue

            config_file = [conf for conf in os.listdir(config_dir)
                           if conf.endswith('.yml') or
                           conf.endswith('.yaml')][0]

            if config_file:
                self.load_webhook_from_config(config_dir, config_file)

    def load_webhook_from_config(self, config_dir, config_file):
        try:
            with open(os.path.join(config_dir, config_file)) as f:
                config = yaml.load(f)

                if config['type'] not in self.webhooks.keys():
                    self.webhooks[config['type']] = []

                path = os.path.normpath(os.path.join(config_dir, '..'))

                try:
                    with open(os.path.join(path, 'static/style.css'), 'r') as f:
                        css_styles = f.read().replace('\n', '')
                except IOError:
                    css_styles = ''

                config.update({
                    'path': path,
                    'css_styles': css_styles
                })
                self.webhooks[config['type']].append(config)
        except Exception as e:
            log.exception(e)
