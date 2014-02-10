from __future__ import absolute_import  # Need to import lwr_client absolutely.
from ..objectstore import ObjectStore
try:
    from galaxy.jobs.runners.lwr_client.manager import ObjectStoreClientManager
except ImportError:
    from lwr.lwr_client.manager import ObjectStoreClientManager


class LwrObjectStore(ObjectStore):
    """
    Object store implementation that delegates to a remote LWR server.

    This may be more aspirational than practical for now, it would be good to
    Galaxy to a point that a handler thread could be setup that doesn't attempt
    to access the disk files returned by a (this) object store - just passing
    them along to the LWR unmodified. That modification - along with this
    implementation and LWR job destinations would then allow Galaxy to fully
    manage jobs on remote servers with completely different mount points.

    This implementation should be considered beta and may be dropped from
    Galaxy at some future point or significantly modified.
    """

    def __init__(self, config, config_xml):
        self.lwr_client = self.__build_lwr_client(config_xml)

    def exists(self, obj, **kwds):
        return self.lwr_client.exists(**self.__build_kwds(obj, **kwds))

    def file_ready(self, obj, **kwds):
        return self.lwr_client.file_ready(**self.__build_kwds(obj, **kwds))

    def create(self, obj, **kwds):
        return self.lwr_client.create(**self.__build_kwds(obj, **kwds))

    def empty(self, obj, **kwds):
        return self.lwr_client.empty(**self.__build_kwds(obj, **kwds))

    def size(self, obj, **kwds):
        return self.lwr_client.size(**self.__build_kwds(obj, **kwds))

    def delete(self, obj, **kwds):
        return self.lwr_client.delete(**self.__build_kwds(obj, **kwds))

    # TODO: Optimize get_data.
    def get_data(self, obj, **kwds):
        return self.lwr_client.get_data(**self.__build_kwds(obj, **kwds))

    def get_filename(self, obj, **kwds):
        return self.lwr_client.get_filename(**self.__build_kwds(obj, **kwds))

    def update_from_file(self, obj, **kwds):
        return self.lwr_client.update_from_file(**self.__build_kwds(obj, **kwds))

    def get_store_usage_percent(self):
        return self.lwr_client.get_store_usage_percent()

    def get_object_url(self, obj, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        return None

    def __build_kwds(self, obj, **kwds):
        kwds['object_id'] = obj.id
        return kwds
        pass

    def __build_lwr_client(self, config_xml):
        url = config_xml.get("url")
        private_token = config_xml.get("private_token", None)
        transport = config_xml.get("transport", None)
        manager_options = dict(transport=transport)
        client_options = dict(url=url, private_token=private_token)
        lwr_client = ObjectStoreClientManager(**manager_options).get_client(client_options)
        return lwr_client

    def shutdown(self):
        pass
