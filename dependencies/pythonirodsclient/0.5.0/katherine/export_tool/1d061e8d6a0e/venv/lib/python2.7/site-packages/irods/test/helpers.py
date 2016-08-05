import os
import tempfile
import contextlib
import shutil


def make_object(session, path, content=None):
    if not content:
        content = 'blah'

    obj = session.data_objects.create(path)
    with obj.open('w') as obj_desc:
        obj_desc.write(content)

    # refresh object after write
    return session.data_objects.get(path)


def make_collection(session, path, filenames=None):
    # create collection
    coll = session.collections.create(path)

    # create objects
    if filenames:
        for name in filenames:
            obj_path = os.path.join(path, name)
            make_object(session, obj_path)

    # return collection
    return coll


def make_dummy_collection(session, path, obj_count):
    coll = session.collections.create(path)

    for n in range(obj_count):
        obj_path = path + "/dummy" + str(n).zfill(6) + ".txt"
        make_object(session, obj_path)

    return coll


@contextlib.contextmanager
def file_backed_up(filename):
    with tempfile.NamedTemporaryFile(prefix=os.path.basename(filename)) as f:
        shutil.copyfile(filename, f.name)
        try:
            yield filename
        finally:
            shutil.copyfile(f.name, filename)