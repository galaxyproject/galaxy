"""This module contains an interface and implementation describing Galaxy interactions used by gxformat2.

The interface is :class:`ImporterGalaxyInterface` and the default
implementation based on `bioblend <http://bioblend.readthedocs.io/>`__
is :class:`BioBlendImporterGalaxyInterface`.
"""
import abc

import bioblend
import six


@six.add_metaclass(abc.ABCMeta)
class ImporterGalaxyInterface(object):
    """An abstract interface describing Galaxy operations used by gxformat2.

    Specifically containing definitions of operations required to load
    workflows into Galaxy.
    """

    @abc.abstractmethod
    def import_workflow(self, workflow, **kwds):
        """Import a workflow via POST /api/workflows or comparable interface into Galaxy."""


class BioBlendImporterGalaxyInterface(object):
    """Implementation of :class:`ImporterGalaxyInterface` using bioblend."""

    def __init__(self, **kwds):
        """Build a :class:`bioblend.GalaxyInstance` from supplied arguments."""
        url = None

        admin_key = None
        admin_gi = None
        if "admin_gi" in kwds:
            admin_gi = kwds["admin_gi"]
        elif "gi" in kwds:
            admin_gi = kwds["gi"]
        elif "url" in kwds and "admin_key" in kwds:
            url = kwds["url"]
            admin_key = kwds["admin_key"]

        if admin_gi is None:
            assert url is not None
            assert admin_key is not None
            admin_gi = bioblend.GalaxyInstance(url=url, key=admin_key)

        user_key = None
        user_gi = None
        if "user_gi" in kwds:
            user_gi = kwds["user_gi"]
        elif "gi" in kwds:
            user_gi = kwds["gi"]
        elif "url" in kwds and "user_key" in kwds:
            url = kwds["url"]
            user_key = kwds["user_key"]

        if user_gi is None:
            assert url is not None
            assert user_key is not None
            user_gi = bioblend.GalaxyInstance(url=url, key=user_key)

        self._admin_gi = admin_gi
        self._user_gi = user_gi

    def import_workflow(self, workflow, **kwds):
        """Import Galaxy workflow using instance :class:`bioblend.GalaxyInstance` object."""
        return self._user_gi.workflows.import_workflow_json(
            workflow,
            **kwds
        )

    def import_tool(self, tool_representation):
        """Import Galaxy tool using instance :class:`bioblend.GalaxyInstance` object."""
        pass
