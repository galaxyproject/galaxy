import itertools
import sqlite3
from threading import RLock
from time import time

import uwsgi

realtime_db_file = uwsgi.opt["interactivetools_map"].decode("utf-8")
db_conn = sqlite3.connect(realtime_db_file)

DATABASE_TABLE_NAME = "gxitproxy"


class CacheEntry:
    def __init__(self, key, value, ttl=20):
        self.key = key
        self.value = value
        self.expires_at = time() + ttl
        self._expired = False

    def expired(self):
        if self._expired is False:
            return self.expires_at < time()
        else:
            return self._expired


class CacheList:
    def __init__(self):
        self.entries = []
        self.lock = RLock()

    def add_entry(self, key, value, ttl=20):
        with self.lock:
            self.entries.append(CacheEntry(key, value, ttl))

    def read_entries(self):
        with self.lock:
            self.entries = list(itertools.dropwhile(lambda x: x.expired(), self.entries))
            return self.entries

    def get_entry_value(self, key, default=None):
        entries = self.read_entries()
        for entry in entries:
            if entry.key == key:
                return entry.value
        return default


key_type_token_mapped_cache = CacheList()


def args_as_unicode(func):
    def wrap_args(*args):
        args = (arg.decode("utf-8") if isinstance(arg, bytes) else arg for arg in args)
        return func(*args)

    return wrap_args


@args_as_unicode
def key_type_token_mapper_cached(key, key_type, token, route_extra, url, ttl):
    global key_type_token_mapped_cache
    cache_key = (key, key_type, token)
    entry = key_type_token_mapped_cache.get_entry_value(cache_key, None)
    if entry is None:
        entry = key_type_token_mapper(key, key_type, token, route_extra, url)
        if entry is not None:
            # Should we cache empty/not authorized entries, perhaps for shorter time?
            key_type_token_mapped_cache.add_entry(cache_key, entry, ttl=float(ttl))
    return entry


@args_as_unicode
def key_type_token_mapper(key, key_type, token, route_extra, url):
    global db_conn
    # print 'key %s key_type %s token %s route_extra %s url %s\n' % (key, key_type, token, route_extra, url)
    if key and key_type and token:
        # sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread. The object was created in thread id x and this is thread id y.
        # So try up to 2 times
        for _ in range(2):
            # Order by rowid gives us the last row added
            try:
                row = db_conn.execute(
                    "SELECT host, port FROM %s WHERE key=? AND key_type=? AND token=? ORDER BY rowid DESC LIMIT 1"
                    % (DATABASE_TABLE_NAME),
                    (key, key_type, token),
                ).fetchone()
                if row:
                    rval = "%s:%s" % (tuple(row))
                    return rval.encode()
                break
            except sqlite3.ProgrammingError:
                db_conn = sqlite3.connect(realtime_db_file)
                continue
            break
    return None


uwsgi.register_rpc("rtt_key_type_token_mapper", key_type_token_mapper)
uwsgi.register_rpc("rtt_key_type_token_mapper_cached", key_type_token_mapper_cached)
