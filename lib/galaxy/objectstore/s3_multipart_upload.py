#!/usr/bin/env python
"""
Split large file into multiple pieces for upload to S3.
This parallelizes the task over available cores using multiprocessing.
Code mostly taken form CloudBioLinux.
"""

import glob
import os
import subprocess
import threading

try:
    import boto
    from boto.s3.connection import S3Connection
except ImportError:
    boto = None  # type: ignore[assignment]


def mp_from_ids(s3server, mp_id, mp_keyname, mp_bucketname):
    """Get the multipart upload from the bucket and multipart IDs.

    This allows us to reconstitute a connection to the upload
    from within multiprocessing functions.
    """
    if s3server["host"]:
        conn = boto.connect_s3(
            aws_access_key_id=s3server["access_key"],
            aws_secret_access_key=s3server["secret_key"],
            is_secure=s3server["is_secure"],
            host=s3server["host"],
            port=s3server["port"],
            calling_format=boto.s3.connection.OrdinaryCallingFormat(),
            path=s3server["conn_path"],
        )
    else:
        if s3server["access_key"]:
            conn = S3Connection(s3server["access_key"], s3server["secret_key"])
        else:
            conn = S3Connection()

    bucket = conn.lookup(mp_bucketname)
    mp = boto.s3.multipart.MultiPartUpload(bucket)
    mp.key_name = mp_keyname
    mp.id = mp_id
    return mp


def transfer_part(s3server, mp_id, mp_keyname, mp_bucketname, i, part):
    """Transfer a part of a multipart upload. Designed to be run in parallel."""
    mp = mp_from_ids(s3server, mp_id, mp_keyname, mp_bucketname)
    with open(part, "rb") as t_handle:
        mp.upload_part_from_file(t_handle, i + 1)
    os.remove(part)


def multipart_upload(s3server, bucket, s3_key_name, tarball, mb_size):
    """Upload large files using Amazon's multipart upload functionality."""

    def split_file(in_file, mb_size, split_num=5):
        prefix = os.path.join(os.path.dirname(in_file), f"{os.path.basename(s3_key_name)}S3PART")
        max_chunk = s3server["max_chunk_size"]
        # Split chunks so they are 5MB < chunk < 250MB(max_chunk_size)
        split_size = int(max(min(mb_size / (split_num * 2.0), max_chunk), 5))
        if not os.path.exists(f"{prefix}aa"):
            cl = ["split", f"-b{split_size}m", in_file, prefix]
            subprocess.check_call(cl)
        return sorted(glob.glob(f"{prefix}*"))

    mp = bucket.initiate_multipart_upload(s3_key_name, reduced_redundancy=s3server["use_rr"])

    for (i, part) in enumerate(split_file(tarball, mb_size)):
        t = threading.Thread(target=transfer_part, args=(s3server, mp.id, mp.key_name, mp.bucket_name, i, part))
        t.start()
        t.join()

    mp.complete_upload()
