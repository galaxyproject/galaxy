"""
This module manages loading of Galaxy webhooks.
"""
import io
import logging
import os

import yaml

from galaxy.util import config_directories_from_setting

log = logging.getLogger(__name__)


class Webhook(object):
    def __init__(self, id, type, activate, weight, path):
        self.id = id
        self.type = type
        self.activate = activate
        self.weight = weight
        self.path = path
        self.styles = ''
        self.script = ''
        self.helper = ''
        self.config = {}

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'activate': self.activate,
            'weight': self.weight,
            'styles': self.styles,
            'script': self.script,
            'config': self.config,
        }


class WebhooksRegistry(object):
    def __init__(self, webhooks_dirs):
        self.webhooks = []
        self.webhooks_directories = []

        for webhook_dir in config_directories_from_setting(webhooks_dirs):
            for plugin_dir in os.listdir(webhook_dir):
                path = os.path.join(webhook_dir, plugin_dir)
                if os.path.isdir(path):
                    self.webhooks_directories.append(path)

        self.load_webhooks()

    def load_webhooks(self):
        for directory in self.webhooks_directories:
            config_file_path = None
            for config_file in ['config.yml', 'config.yaml']:
                path = os.path.join(directory, config_file)
                if os.path.isfile(path):
                    config_file_path = path
                    break

            if config_file_path:
                try:
                    self.load_webhook_from_config(directory, config_file_path)
                except Exception as e:
                    log.exception(e)

    def load_webhook_from_config(self, webhook_dir, config_file_path):
        with open(config_file_path) as fh:
            config = yaml.safe_load(fh)

        weight = config.get('weight', 1)
        if weight < 1:
            raise ValueError('Webhook weight must be greater or equal 1.')

        webhook = Webhook(
            config.get('id'),
            config.get('type'),
            config.get('activate', False),
            weight,
            webhook_dir,
        )

        # Read styles into a string, assuming all styles are in a
        # single file
        try:
            styles_file = os.path.join(webhook_dir, 'styles.css')
            with open(styles_file, 'r') as fh:
                webhook.styles = fh.read().replace('\n', '')
        except IOError:
            pass

        # Read script into a string, assuming everything is in a
        # single file
        try:
            script_file = os.path.join(webhook_dir, 'script.js')
            with io.open(script_file, 'r', encoding='utf-8') as fh:
                webhook.script = fh.read()
        except IOError:
            pass

        # Save helper function path if it exists
        helper_path = os.path.join(webhook_dir, '__init__.py')
        if os.path.isfile(helper_path):
            webhook.helper = helper_path

        webhook.config = config
        self.webhooks.append(webhook)
