import fcntl

from galaxy.util import unicodify


def fork_safe_write(path: str, contents: str):
    # The following write method looks a little funky and is inspired by https://twitter.com/_monoid/status/1317895053122150400.
    # This should guarantee that we wait until all forks that inherit open FDs have proceeded to execve,
    # because only then the shared lock can be acquired.
    # This **should** entirely avoid the "Text File Busy" error that `_handle_script_integrity` attempts to deal with.
    # The likelihood of "Text File Busy" happening increases as the load increases, and more work has to be done
    # when forking to copy memory pages, making the fork slower and therefore more likely to happen while the script
    # file is open for writing.
    with open(path, "w", encoding="utf-8") as f:
        f.write(unicodify(contents))
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    with open(path) as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
