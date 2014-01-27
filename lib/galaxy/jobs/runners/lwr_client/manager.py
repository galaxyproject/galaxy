from abc import ABCMeta, abstractmethod
try:
    from Queue import Queue
except ImportError:
    from queue import Queue
from threading import Thread
from os import getenv
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode
try:
    from StringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO
try:
    from six import text_type
except ImportError:
    from galaxy.util import unicodify as text_type

from .client import JobClient
from .client import InputCachingJobClient
from .client import ObjectStoreClient
from .transport import get_transport
from .util import TransferEventManager
from .destination import url_to_destination_params


from logging import getLogger
log = getLogger(__name__)

DEFAULT_TRANSFER_THREADS = 2


class ClientManager(object):
    """
    Factory to create LWR clients, used to manage potential shared
    state between multiple client connections.
    """
    def __init__(self, **kwds):
        if 'job_manager' in kwds:
            self.job_manager_interface_class = LocalLwrInterface
            self.job_manager_interface_args = dict(job_manager=kwds['job_manager'], file_cache=kwds['file_cache'])
        else:
            self.job_manager_interface_class = HttpLwrInterface
            transport_type = kwds.get('transport_type', None)
            transport = get_transport(transport_type)
            self.job_manager_interface_args = dict(transport=transport)
        cache = kwds.get('cache', None)
        if cache is None:
            cache = _environ_default_int('LWR_CACHE_TRANSFERS')
        if cache:
            log.info("Setting LWR client class to caching variant.")
            self.client_cacher = ClientCacher(**kwds)
            self.client_class = InputCachingJobClient
            self.extra_client_kwds = {"client_cacher": self.client_cacher}
        else:
            log.info("Setting LWR client class to standard, non-caching variant.")
            self.client_class = JobClient
            self.extra_client_kwds = {}

    def get_client(self, destination_params, job_id):
        destination_params = self.__parse_destination_params(destination_params)
        job_manager_interface_class = self.job_manager_interface_class
        job_manager_interface_args = dict(destination_params=destination_params, **self.job_manager_interface_args)
        job_manager_interface = job_manager_interface_class(**job_manager_interface_args)
        return self.client_class(destination_params, job_id, job_manager_interface, **self.extra_client_kwds)

    def __parse_destination_params(self, destination_params):
        try:
            unicode_type = unicode
        except NameError:
            unicode_type = str
        if isinstance(destination_params, str) or isinstance(destination_params, unicode_type):
            destination_params = url_to_destination_params(destination_params)
        return destination_params


class ObjectStoreClientManager(object):

    def __init__(self, **kwds):
        if 'object_store' in kwds:
            self.interface_class = LocalLwrInterface
            self.interface_args = dict(object_store=kwds['object_store'])
        else:
            self.interface_class = HttpLwrInterface
            transport_type = kwds.get('transport_type', None)
            transport = get_transport(transport_type)
            self.interface_args = dict(transport=transport)
        self.extra_client_kwds = {}

    def get_client(self, client_params):
        interface_class = self.interface_class
        interface_args = dict(destination_params=client_params, **self.interface_args)
        interface = interface_class(**interface_args)
        return ObjectStoreClient(interface)


class JobManagerInteface(object):
    """
    Abstract base class describes how client communicates with remote job
    manager.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def execute(self, command, args={}, data=None, input_path=None, output_path=None):
        """
        Execute the correspond command against configured LWR job manager. Arguments are
        method parameters and data or input_path describe essentially POST bodies. If command
        results in a file, resulting path should be specified as output_path.
        """


class HttpLwrInterface(object):

    def __init__(self, destination_params, transport):
        self.transport = transport
        self.remote_host = destination_params.get("url")
        assert self.remote_host is not None, "Failed to determine url for LWR client."
        self.private_key = destination_params.get("private_token", None)

    def execute(self, command, args={}, data=None, input_path=None, output_path=None):
        url = self.__build_url(command, args)
        response = self.transport.execute(url, data=data, input_path=input_path, output_path=output_path)
        return response

    def __build_url(self, command, args):
        if self.private_key:
            args["private_key"] = self.private_key
        arg_bytes = dict([(k, text_type(args[k]).encode('utf-8')) for k in args])
        data = urlencode(arg_bytes)
        url = self.remote_host + command + "?" + data
        return url


class LocalLwrInterface(object):

    def __init__(self, destination_params, job_manager=None, file_cache=None, object_store=None):
        self.job_manager = job_manager
        self.file_cache = file_cache
        self.object_store = object_store

    def __app_args(self):
        ## Arguments that would be specified from LwrApp if running
        ## in web server.
        return {
            'manager': self.job_manager,
            'file_cache': self.file_cache,
            'object_store': self.object_store,
            'ip': None
        }

    def execute(self, command, args={}, data=None, input_path=None, output_path=None):
        # If data set, should be unicode (on Python 2) or str (on Python 3).
        from lwr import routes
        from lwr.framework import build_func_args
        controller = getattr(routes, command)
        action = controller.func
        body_args = dict(body=self.__build_body(data, input_path))
        args = build_func_args(action, args.copy(), self.__app_args(), body_args)
        result = action(**args)
        if controller.response_type != 'file':
            return controller.body(result)
        else:
            from lwr.util import copy_to_path
            with open(result, 'rb') as result_file:
                copy_to_path(result_file, output_path)

    def __build_body(self, data, input_path):
        if data is not None:
            return BytesIO(data.encode('utf-8'))
        elif input_path is not None:
            return open(input_path, 'rb')
        else:
            return None


class ClientCacher(object):

    def __init__(self, **kwds):
        self.event_manager = TransferEventManager()
        default_transfer_threads = _environ_default_int('LWR_CACHE_THREADS', DEFAULT_TRANSFER_THREADS)
        num_transfer_threads = int(kwds.get('transfer_threads', default_transfer_threads))
        self.__init_transfer_threads(num_transfer_threads)

    def queue_transfer(self, client, path):
        self.transfer_queue.put((client, path))

    def acquire_event(self, input_path):
        return self.event_manager.acquire_event(input_path)

    def _transfer_worker(self):
        while True:
            transfer_info = self.transfer_queue.get()
            try:
                self.__perform_transfer(transfer_info)
            except BaseException as e:
                log.warn("Transfer failed.")
                log.exception(e)
                pass
            self.transfer_queue.task_done()

    def __perform_transfer(self, transfer_info):
        (client, path) = transfer_info
        event_holder = self.event_manager.acquire_event(path, force_clear=True)
        failed = True
        try:
            client.cache_insert(path)
            failed = False
        finally:
            event_holder.failed = failed
            event_holder.release()

    def __init_transfer_threads(self, num_transfer_threads):
        self.num_transfer_threads = num_transfer_threads
        self.transfer_queue = Queue()
        for i in range(num_transfer_threads):
            t = Thread(target=self._transfer_worker)
            t.daemon = True
            t.start()


def _environ_default_int(variable, default="0"):
    val = getenv(variable, default)
    int_val = int(default)
    if str(val).isdigit():
        int_val = int(val)
    return int_val

__all__ = [ClientManager, ObjectStoreClientManager, HttpLwrInterface]
