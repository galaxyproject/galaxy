"""
Abstract base class for runners which execute commands via a shell.
"""
from abc import ABCMeta, abstractmethod


class BaseShellExec(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, *args, **kwargs):
        """
        Constructor for shell executor instance.
        """

    def execute(self, cmd, persist=False, timeout=60):
        """
        Execute the specified command via defined shell.
        """
