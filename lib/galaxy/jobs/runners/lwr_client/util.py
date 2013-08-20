from threading import Lock, Event
from weakref import WeakValueDictionary


class TransferEventManager(object):

    def __init__(self):
        self.events = WeakValueDictionary(dict())
        self.events_lock = Lock()

    def acquire_event(self, path, force_clear=False):
        with self.events_lock:
            if path in self.events:
                event_holder = self.events[path]
            else:
                event_holder = EventHolder(Event(), path, self)
                self.events[path] = event_holder
        if force_clear:
            event_holder.event.clear()
        return event_holder


class EventHolder(object):

    def __init__(self, event, path, condition_manager):
        self.event = event
        self.path = path
        self.condition_manager = condition_manager

    def release(self):
        self.event.set()
