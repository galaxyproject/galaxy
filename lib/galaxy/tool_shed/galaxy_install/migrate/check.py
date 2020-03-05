import logging
import os
import sys

from migrate.versioning import repository, schema

log = logging.getLogger(__name__)

# Path relative to galaxy
migrate_repository_directory = os.path.abspath(os.path.dirname(__file__)).replace(os.getcwd() + os.path.sep, '', 1)
migrate_repository = repository.Repository(migrate_repository_directory)


def migrate_to_current_version(engine):
    # Changes to get to current version.
    changeset = schema.changeset(None)
    for ver, change in changeset:
        nextver = ver + changeset.step
        log.info('Installing tools from version %s -> %s... ' % (ver, nextver))
        old_stdout = sys.stdout

        class FakeStdout(object):
            def __init__(self):
                self.buffer = []

            def write(self, s):
                self.buffer.append(s)

            def flush(self):
                pass

        sys.stdout = FakeStdout()
        try:
            schema.runchange(ver, change, changeset.step)
        finally:
            for message in "".join(sys.stdout.buffer).split("\n"):
                log.info(message)
            sys.stdout = old_stdout
