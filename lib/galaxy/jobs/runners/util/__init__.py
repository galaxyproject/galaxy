"""
This module and its submodules contains utilities for running external
processes and interfacing with job managers. This module should contain
functionality shared between Galaxy and the LWR.
"""
from galaxy.util.bunch import Bunch

from .kill import kill_pid

__all__ = [kill_pid, Bunch]
