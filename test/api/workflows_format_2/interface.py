import abc
import json

import bioblend
import six


@six.add_metaclass(abc.ABCMeta)
class ImporterGalaxyInterface(object):
    """ An abstract interface describing the interaction between
    Galaxy and the workflow import code.
    """

    @abc.abstractmethod
    def import_workflow(self, workflow, **kwds):
        """ Import a workflow via POST /api/workflows or
        comparable interface into Galaxy.
        """
        pass


class BioBlendImporterGalaxyInterface(object):

    def __init__(self, **kwds):
        """
        """
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
        workflow_str = json.dumps(workflow, indent=4)
        return self._user_gi.workflows.import_workflow_json(
            workflow_str,
            **kwds
        )

    def import_tool(self, tool_representation):
        pass
