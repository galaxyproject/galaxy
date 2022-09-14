import os
import sys
import threading
import time
import traceback


def get_current_thread_object_dict():
    """
    Get a dictionary of all 'Thread' objects created via the threading
    module keyed by thread_id. Note that not all interpreter threads
    have a thread objects, only the main thread and any created via the
    'threading' module. Threads created via the low level 'thread' module
    will not be in the returned dictionary.

    HACK: This mucks with the internals of the threading module since that
          module does not expose any way to match 'Thread' objects with
          intepreter thread identifiers (though it should).
    """
    rval = dict()
    # Acquire the lock and then union the contents of 'active' and 'limbo'
    # threads into the return value.
    threading._active_limbo_lock.acquire()
    rval.update(threading._active)
    rval.update(threading._limbo)
    threading._active_limbo_lock.release()
    return rval


class Heartbeat(threading.Thread):
    """
    Thread that periodically dumps the state of all threads to a file
    """

    def __init__(self, config, name="Heartbeat Thread", period=20, fname="heartbeat.log"):
        threading.Thread.__init__(self, name=name)
        self.config = config
        self.should_stop = False
        self.period = period
        self.fname = fname
        self.file = None
        self.fname_nonsleeping = None
        self.file_nonsleeping = None
        self.pid = None
        self.nonsleeping_heartbeats = {}
        # Event to wait on when sleeping, allows us to interrupt for shutdown
        self.wait_event = threading.Event()

    def run(self):
        self.pid = os.getpid()
        self.fname = self.fname.format(server_name=self.config.server_name, pid=self.pid)
        fname, ext = os.path.splitext(self.fname)
        self.fname_nonsleeping = f"{fname}.nonsleeping{ext}"
        wait = self.period
        if self.period <= 0:
            wait = 60
        while not self.should_stop:
            if self.period > 0:
                self.dump()
            self.wait_event.wait(wait)

    def open_logs(self):
        if self.file is None or self.file.closed:
            self.file = open(self.fname, "a")
            self.file_nonsleeping = open(self.fname_nonsleeping, "a")
            self.file.write("Heartbeat for pid %d thread started at %s\n\n" % (self.pid, time.asctime()))
            self.file_nonsleeping.write(
                "Non-Sleeping-threads for pid %d thread started at %s\n\n" % (self.pid, time.asctime())
            )

    def close_logs(self):
        if self.file is not None and not self.file.closed:
            self.file.write("Heartbeat for pid %d thread stopped at %s\n\n" % (self.pid, time.asctime()))
            self.file_nonsleeping.write(
                "Non-Sleeping-threads for pid %d thread stopped at %s\n\n" % (self.pid, time.asctime())
            )
            self.file.close()
            self.file_nonsleeping.close()

    def dump(self):
        self.open_logs()
        try:
            # Print separator with timestamp
            self.file.write(f"Traceback dump for all threads at {time.asctime()}:\n\n")
            # Print the thread states
            threads = get_current_thread_object_dict()
            for thread_id, frame in sys._current_frames().items():
                if thread_id in threads:
                    object = repr(threads[thread_id])
                else:
                    object = "<No Thread object>"
                self.file.write(f"Thread {thread_id}, {object}:\n\n")
                traceback.print_stack(frame, file=self.file)
                self.file.write("\n")
            self.file.write("End dump\n\n")
            self.file.flush()
            self.print_nonsleeping(threads)
        except Exception:
            self.file.write("Caught exception attempting to dump thread states:")
            traceback.print_exc(None, self.file)
            self.file.write("\n")

    def shutdown(self):
        self.should_stop = True
        self.wait_event.set()
        self.close_logs()
        self.join()

    def thread_is_sleeping(self, last_stack_frame):
        """
        Returns True if the given stack-frame represents a known
        sleeper function (at least in python 2.5)
        """
        _filename = last_stack_frame[0]
        # _line = last_stack_frame[1]
        _funcname = last_stack_frame[2]
        _text = last_stack_frame[3]
        # Ugly hack to tell if a thread is supposedly sleeping or not
        # These are the most common sleeping functions I've found.
        # Is there a better way? (python interpreter internals?)
        # Tested only with python 2.5
        if _funcname == "wait" and _text == "waiter.acquire()":
            return True
        if _funcname == "wait" and _text == "_sleep(delay)":
            return True
        if _funcname == "accept" and _text[-14:] == "_sock.accept()":
            return True
        if (
            _funcname in ("monitor", "__monitor", "app_loop", "check")
            and _text.startswith("time.sleep(")
            and _text.endswith(")")
        ):
            return True
        if _funcname == "drain_events" and _text == "sleep(polling_interval)":
            return True
        # Ugly hack: always skip the heartbeat thread
        # TODO: get the current thread-id in python
        #   skip heartbeat thread by thread-id, not by filename
        if _filename.find("/lib/galaxy/util/heartbeat.py") != -1:
            return True
        # By default, assume the thread is not sleeping
        return False

    def get_interesting_stack_frame(self, stack_frames):
        """
        Scans a given backtrace stack frames, returns a single
        quadraple of [filename, line, function-name, text] of
        the single, deepest, most interesting frame.

        Interesting being::

          inside the galaxy source code ("/lib/galaxy"),
          prefreably not an egg.
        """
        for _filename, _line, _funcname, _text in reversed(stack_frames):
            idx = _filename.find("/lib/galaxy/")
            if idx != -1:
                relative_filename = _filename[idx:]
                return (relative_filename, _line, _funcname, _text)
        # no "/lib/galaxy" code found, return the innermost frame
        return stack_frames[-1]

    def print_nonsleeping(self, threads_object_dict):
        self.file_nonsleeping.write(f"Non-Sleeping threads at {time.asctime()}:\n\n")
        all_threads_are_sleeping = True
        threads = get_current_thread_object_dict()
        for thread_id, frame in sys._current_frames().items():
            if thread_id in threads:
                object = repr(threads[thread_id])
            else:
                object = "<No Thread object>"
            tb = traceback.extract_stack(frame)
            if self.thread_is_sleeping(tb[-1]):
                if thread_id in self.nonsleeping_heartbeats:
                    del self.nonsleeping_heartbeats[thread_id]
                continue

            # Count non-sleeping thread heartbeats
            if thread_id in self.nonsleeping_heartbeats:
                self.nonsleeping_heartbeats[thread_id] += 1
            else:
                self.nonsleeping_heartbeats[thread_id] = 1

            good_frame = self.get_interesting_stack_frame(tb)
            self.file_nonsleeping.write(
                'Thread %s\t%s\tnon-sleeping for %d heartbeat(s)\n  File %s:%d\n    Function "%s"\n      %s\n'
                % (
                    thread_id,
                    object,
                    self.nonsleeping_heartbeats[thread_id],
                    good_frame[0],
                    good_frame[1],
                    good_frame[2],
                    good_frame[3],
                )
            )
            all_threads_are_sleeping = False

        if all_threads_are_sleeping:
            self.file_nonsleeping.write("All threads are sleeping.\n")
        self.file_nonsleeping.write("\n")
        self.file_nonsleeping.flush()

    def dump_signal_handler(self, signum, frame):
        self.dump()
