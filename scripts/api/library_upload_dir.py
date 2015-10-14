#!/usr/bin/env python
import sys
import argparse
import os
from bioblend import galaxy


class Uploader:

    def __init__(self, url, api, library_id, folder_id, should_link):
        self.gi = galaxy.GalaxyInstance(url=url, key=api)
        self.library_id = library_id
        self.folder_id = folder_id
        self.should_link

        self.memo_path = {}

    def memoized_path(self, path_parts, base_folder=None):
        """Get the folder ID for a given folder path specified by path_parts.

        If the folder does not exist, it will be created ONCE (during the
        instantiation of this Uploader object). After that it is stored and
        recycled. If the Uploader object is re-created, it is not aware of
        previously existing paths and will not respect those. TODO: handle
        existing paths.
        """
        if base_folder is None:
            base_folder = self.folder_id
        dropped_prefix = []

        fk = '/'.join(path_parts)
        if fk in self.memo_path:
            # print "Cache hit %s" % fk
            return self.memo_path[fk]
        else:
            # print "Cache miss %s" % fk
            for i in reversed(range(len(path_parts))):
                fk = '/'.join(path_parts[0:i + 1])
                if fk in self.memo_path:
                    # print "Parent folder hit %s" % fk
                    dropped_prefix = path_parts[0:i + 1]
                    path_parts = path_parts[i + 1:]
                    base_folder = self.memo_path[fk]
                    break

        nfk = []
        for i in range(len(path_parts)):
            nfk.append('/'.join(list(dropped_prefix) + list(path_parts[0:i + 1])))

        # Recursively create the path from our base_folder starting points,
        # gettting the IDs of each folder per path component
        ids = self.recursively_build_path(path_parts, base_folder)

        # These are then associated with the paths.
        for (key, fid) in zip(nfk, ids):
            self.memo_path[key] = fid
        return ids[-1]

    def recursively_build_path(self, path_parts, parent_folder_id, ids=None):
        """Given an iterable of path components and a parent folder id, recursively
        create directories below parent_folder_id"""
        if ids is None:
            ids = []
        if len(path_parts) == 0:
            return ids
        else:
            pf = self.gi.libraries.create_folder(self.library_id, path_parts[0], base_folder_id=parent_folder_id)
            ids.append(pf[0]['id'])
            # print "create_folder(%s, %s, %s) = %s" % (self.library_id, path_parts[0], parent_folder_id, pf[0]['id'])
            return self.recursively_build_path(path_parts[1:], pf[0]['id'], ids=ids)

    # http://stackoverflow.com/questions/13505819/python-split-path-recursively/13505966#13505966
    def rec_split(self, s):
        rest, tail = os.path.split(s)
        if tail == '.':
            return ()
        if rest == '':
            return tail,
        return self.rec_split(rest) + (tail,)

    def upload(self):
        all_files = [x.strip() for x in list(sys.stdin.readlines())]

        for idx, (dirName, fname) in enumerate(all_files):
            if idx < 35:
                continue
            if not os.path.exists(os.path.join(dirName, fname)):
                continue
            fid = self.memoized_path(self.rec_split(dirName), base_folder=self.folder_id)
            print('[%s/%s] %s/%s' % (idx, len(all_files), fid, fname))
            print self.gi.libraries.upload_file_from_local_path(
                self.library_id,
                os.path.join(dirName, fname),
                folder_id=fid,
                link_data_only=self.should_link,
            )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Upload a directory into a data library')
    parser.add_argument( "-u", "--url", dest="url", required=True, help="Galaxy URL" )
    parser.add_argument( "-a", "--api", dest="api", required=True, help="API Key" )

    parser.add_argument( "-l", "--lib", dest="library_id", required=True, help="Library ID" )
    parser.add_argument( "-f", "--folder", dest="folder_id", help="Folder ID. If not specified, will go to root of library." )

    parser.add_argument( "--link", dest="should_link", action="store_true", default=False, help="Link datasets only, do not upload to Galaxy.")
    args = parser.parse_args()

    u = Uploader(**vars(args))
    u.upload()
