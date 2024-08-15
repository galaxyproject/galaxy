from . import BaseObjectStore

try:
    from pulsar.client.manager import ObjectStoreClientManager
except ImportError:
    ObjectStoreClientManager = None


class PulsarObjectStore(BaseObjectStore):
    """
    Object store implementation that delegates to a remote Pulsar server.

    This may be more aspirational than practical for now, it would be good to
    Galaxy to a point that a handler thread could be setup that doesn't attempt
    to access the disk files returned by a (this) object store - just passing
    them along to the Pulsar unmodified. That modification - along with this
    implementation and Pulsar job destinations would then allow Galaxy to fully
    manage jobs on remote servers with completely different mount points.

    This implementation should be considered beta and may be dropped from
    Galaxy at some future point or significantly modified.
    """

    def __init__(self, config, config_xml):
        self.pulsar_client = self.__build_pulsar_client(config_xml)

    def _exists(self, obj, **kwds) -> bool:
        return self.pulsar_client.exists(**self.__build_kwds(obj, **kwds))

    def file_ready(self, obj, **kwds):
        return self.pulsar_client.file_ready(**self.__build_kwds(obj, **kwds))

    def _create(self, obj, **kwds):
        return self.pulsar_client.create(**self.__build_kwds(obj, **kwds))

    def _empty(self, obj, **kwds) -> bool:
        return self.pulsar_client.empty(**self.__build_kwds(obj, **kwds))

    def _size(self, obj, **kwds) -> int:
        return self.pulsar_client.size(**self.__build_kwds(obj, **kwds))

    def _delete(self, obj, **kwds) -> bool:
        return self.pulsar_client.delete(**self.__build_kwds(obj, **kwds))

    # TODO: Optimize get_data.
    def _get_data(self, obj, **kwds):
        return self.pulsar_client.get_data(**self.__build_kwds(obj, **kwds))

    def _get_filename(self, obj, **kwds) -> str:
        return self.pulsar_client.get_filename(**self.__build_kwds(obj, **kwds))

    def _update_from_file(self, obj, **kwds) -> None:
        return self.pulsar_client.update_from_file(**self.__build_kwds(obj, **kwds))

    def _get_store_usage_percent(self):
        return self.pulsar_client.get_store_usage_percent()

    def _get_object_url(self, obj, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        return None

    def __build_kwds(self, obj, **kwds):
        kwds["object_id"] = obj.id
        return kwds

    def __build_pulsar_client(self, config_xml):
        if ObjectStoreClientManager is None:
            raise Exception("Pulsar client code not available, cannot use this module.")
        url = config_xml.get("url")
        private_token = config_xml.get("private_token", None)
        transport = config_xml.get("transport", None)
        manager_options = dict(transport=transport)
        client_options = dict(url=url, private_token=private_token)
        pulsar_client = ObjectStoreClientManager(**manager_options).get_client(client_options)
        return pulsar_client

    def shutdown(self):
        pass
