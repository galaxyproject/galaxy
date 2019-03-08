import uwsgi
import sqlite3


realtime_db_file = uwsgi.opt["sessions"]
db_conn = sqlite3.connect(realtime_db_file)


def key_type_token_mapper(key, key_type, token, route_extra, url):
    global db_conn
    # print 'key %s key_type %s token %s route_extra %s url %s\n' % (key, key_type, token, route_extra, url)
    if key and key_type and token:
        # sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread. The object was created in thread id x and this is thread id y.
        # So try upto 2 times
        for i in range(2):
            # Order by rowid gives us the last row added
            try:
                row = db_conn.execute("select host, port from gxrtproxy where key=? and key_type=? and token=? order by rowid desc limit 1", (key, key_type, token)).fetchone()
                if row:
                    rval = '%s:%s' % (tuple(row))
                    return rval.encode()
                break
            except sqlite3.ProgrammingError:
                db_conn = sqlite3.connect(realtime_db_file)
                continue
            break
    return None


uwsgi.register_rpc('rtt_key_type_token_mapper', key_type_token_mapper)
