from Queue import Queue
from threading import Thread

from .client import Client, InputCachingClient
from .transport import get_transport
from .util import TransferEventManager

DEFAULT_TRANSFER_THREADS = 2


class ClientManager(object):
    """
    Factory to create LWR clients, used to manage potential shared
    state between multiple client connections.
    """
    def __init__(self, **kwds):
        self.transport = get_transport(kwds.get('transport_type', None))
        self.event_manager = TransferEventManager()
        cache = kwds.get('cache', False)
        if cache:
            self.client_class = InputCachingClient
            num_transfer_threads = int(kwds.get('transfer_threads', DEFAULT_TRANSFER_THREADS))
            self.__init_transfer_threads(num_transfer_threads)
        else:
            self.client_class = Client

    def _transfer_worker(self):
        while True:
            transfer_info = self.transfer_queue.get()
            try:
                self.__perform_transfer(transfer_info)
            except:
                pass
            self.transfer_queue.task_done()

    def __perform_transfer(self, transfer_info):
        (client, path) = transfer_info
        event_holder = self.event_manager.acquire_event(path, force_clear=True)
        client.cache_insert(path)
        event_holder.event.set()

    def __init_transfer_threads(self, num_transfer_threads):
        self.transfer_queue = Queue()
        for i in range(num_transfer_threads):
            t = Thread(target=self._transfer_worker)
            t.daemon = True
            t.start()

    def queue_transfer(self, client, path):
        self.transfer_queue.put((client, path))

    def get_client(self, destination_params, job_id):
        return self.client_class(destination_params, job_id, self)
