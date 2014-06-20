from .decorators import parseJson


class ObjectStoreClient(object):

    def __init__(self, pulsar_interface):
        self.pulsar_interface = pulsar_interface

    @parseJson()
    def exists(self, **kwds):
        return self._raw_execute("object_store_exists", args=self.__data(**kwds))

    @parseJson()
    def file_ready(self, **kwds):
        return self._raw_execute("object_store_file_ready", args=self.__data(**kwds))

    @parseJson()
    def create(self, **kwds):
        return self._raw_execute("object_store_create", args=self.__data(**kwds))

    @parseJson()
    def empty(self, **kwds):
        return self._raw_execute("object_store_empty", args=self.__data(**kwds))

    @parseJson()
    def size(self, **kwds):
        return self._raw_execute("object_store_size", args=self.__data(**kwds))

    @parseJson()
    def delete(self, **kwds):
        return self._raw_execute("object_store_delete", args=self.__data(**kwds))

    @parseJson()
    def get_data(self, **kwds):
        return self._raw_execute("object_store_get_data", args=self.__data(**kwds))

    @parseJson()
    def get_filename(self, **kwds):
        return self._raw_execute("object_store_get_filename", args=self.__data(**kwds))

    @parseJson()
    def update_from_file(self, **kwds):
        return self._raw_execute("object_store_update_from_file", args=self.__data(**kwds))

    @parseJson()
    def get_store_usage_percent(self):
        return self._raw_execute("object_store_get_store_usage_percent", args={})

    def __data(self, **kwds):
        return kwds

    def _raw_execute(self, command, args={}):
        return self.pulsar_interface.execute(command, args, data=None, input_path=None, output_path=None)
