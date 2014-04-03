#!/usr/bin/env python
"""
Split large file into multiple pieces for upload to S3.
This parallelizes the task over available cores using multiprocessing.
Code mostly taken form CloudBioLinux.
"""

import contextlib
import functools
import glob
import multiprocessing
import os
import subprocess

from multiprocessing.pool import IMapIterator

try:
    from galaxy import eggs
    eggs.require('boto')
except ImportError:
    pass

try:
    import boto
    from boto.s3.connection import S3Connection
except ImportError:
    boto = None


def map_wrap(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return apply(f, *args, **kwargs)
    return wrapper


def mp_from_ids(mp_id, mp_keyname, mp_bucketname, aws_access_key_id, aws_secret_access_key):
    """Get the multipart upload from the bucket and multipart IDs.

    This allows us to reconstitute a connection to the upload
    from within multiprocessing functions.
    """
    conn = S3Connection(aws_access_key_id, aws_secret_access_key)
    bucket = conn.lookup(mp_bucketname)
    mp = boto.s3.multipart.MultiPartUpload(bucket)
    mp.key_name = mp_keyname
    mp.id = mp_id
    return mp


@map_wrap
def transfer_part(mp_id, mp_keyname, mp_bucketname, i, part, aws_access_key_id, aws_secret_access_key):
    """Transfer a part of a multipart upload. Designed to be run in parallel.
    """
    mp = mp_from_ids(mp_id, mp_keyname, mp_bucketname, aws_access_key_id, aws_secret_access_key)
    with open(part) as t_handle:
        mp.upload_part_from_file(t_handle, i + 1)
    os.remove(part)


def multipart_upload(bucket, s3_key_name, tarball, mb_size, aws_access_key_id, aws_secret_access_key, use_rr=True):
    """Upload large files using Amazon's multipart upload functionality.
    """
    cores = multiprocessing.cpu_count()

    def split_file(in_file, mb_size, split_num=5):
        prefix = os.path.join(os.path.dirname(in_file),
                              "%sS3PART" % (os.path.basename(s3_key_name)))
        # Split chunks so they are 5MB < chunk < 250MB
        split_size = int(max(min(mb_size / (split_num * 2.0), 250), 5))
        if not os.path.exists("%saa" % prefix):
            cl = ["split", "-b%sm" % split_size, in_file, prefix]
            subprocess.check_call(cl)
        return sorted(glob.glob("%s*" % prefix))

    mp = bucket.initiate_multipart_upload(s3_key_name, reduced_redundancy=use_rr)
    with multimap(cores) as pmap:
        for _ in pmap(transfer_part, ((mp.id, mp.key_name, mp.bucket_name, i, part, aws_access_key_id, aws_secret_access_key)
                                      for (i, part) in
                                      enumerate(split_file(tarball, mb_size, cores)))):
            pass
    mp.complete_upload()


@contextlib.contextmanager
def multimap(cores=None):
    """Provide multiprocessing imap like function.

    The context manager handles setting up the pool, worked around interrupt issues
    and terminating the pool on completion.
    """
    if cores is None:
        cores = max(multiprocessing.cpu_count() - 1, 1)

    def wrapper(func):
        def wrap(self, timeout=None):
            return func(self, timeout=timeout if timeout is not None else 1e100)
        return wrap
    IMapIterator.next = wrapper(IMapIterator.next)
    pool = multiprocessing.Pool(cores)
    yield pool.imap
    pool.terminate()
