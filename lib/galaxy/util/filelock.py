"""Code obtained from https://github.com/dmfrey/FileLock.

See full license at:

https://github.com/dmfrey/FileLock/blob/master/LICENSE.txt

"""

import errno
import os
import time


class FileLockException(Exception):
    pass


class FileLock:
    """A file locking mechanism that has context-manager support so
    you can use it in a with statement. This should be relatively cross
    compatible as it doesn't rely on msvcrt or fcntl for the locking.
    """

    def __init__(self, file_name, timeout=10, delay=0.05):
        """Prepare the file locker. Specify the file to lock and optionally
        the maximum timeout and the delay between each attempt to lock.
        """
        self.is_locked = False
        full_path = os.path.abspath(file_name)
        self.lockfile = f"{full_path}.lock"
        self.file_name = full_path
        self.timeout = timeout
        self.delay = delay

    def acquire(self):
        """Acquire the lock, if possible. If the lock is in use, it check again
        every `wait` seconds. It does this until it either gets the lock or
        exceeds `timeout` number of seconds, in which case it throws
        an exception.
        """
        start_time = time.time()
        while True:
            try:
                self.fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                break
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
                if (time.time() - start_time) >= self.timeout:
                    raise FileLockException("Timeout occurred.")
                time.sleep(self.delay)
        self.is_locked = True

    def release(self):
        """Get rid of the lock by deleting the lockfile.
        When working in a `with` statement, this gets automatically
        called at the end.
        """
        if self.is_locked:
            os.close(self.fd)
            os.unlink(self.lockfile)
            self.is_locked = False

    def __enter__(self):
        """Activated when used in the with statement.
        Should automatically acquire a lock to be used in the with block.
        """
        if not self.is_locked:
            self.acquire()
        return self

    def __exit__(self, type, value, traceback):
        """Activated at the end of the with statement.
        It automatically releases the lock if it isn't locked.
        """
        if self.is_locked:
            self.release()

    def __del__(self):
        """Make sure that the FileLock instance doesn't leave a lockfile
        lying around.
        """
        self.release()
