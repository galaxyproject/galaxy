#!/usr/bin/env python
import argparse
import os
import sys

from bioblend import galaxy


class Uploader:

    def __init__(self, url, api, library_id, folder_id, should_link,
                 non_local):
        self.gi = galaxy.GalaxyInstance(url=url, key=api)
        self.library_id = library_id
        self.folder_id = folder_id
        self.should_link = should_link
        self.non_local = non_local

        self.memo_path = {}
        self.prepopulate_memo()

    def prepopulate_memo(self):
        """
        Because the Galaxy Data Libraries API/system does not act like any
        other file system in existence, and allows multiple files/folders with
        identical names in the same parent directory, we have to prepopulate
        the memoization cache with everything currently in the target
        directory.

        Because the Galaxy Data Libraries API does not work from a perspective
        of "show me what is in this directory", we are forced to get the entire
        contents of the data library, and then filter out things that are
        interesting to us based on a folder prefix.
        """
        existing = self.gi.libraries.show_library(self.library_id, contents=True)

        uploading_to = [x for x in existing if x['id'] == self.folder_id]
        if len(uploading_to) == 0:
            raise Exception("Unknown folder [%s] in library [%s]" %
                            (self.folder_id, self.library_id))
        else:
            uploading_to = uploading_to[0]

        for x in existing:
            # We only care if it's a subdirectory of where we're uploading to
            if not x['name'].startswith(uploading_to['name']):
                continue

            name_part = x['name'].split(uploading_to['name'], 1)[-1]
            if name_part.startswith('/'):
                name_part = name_part[1:]
            self.memo_path[name_part] = x['id']

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
        if s == '/':
            return ()

        rest, tail = os.path.split(s)
        if tail == '.':
            return ()
        if rest == '':
            return tail,
        return self.rec_split(rest) + (tail,)

    def upload(self):
        all_files = [x.strip() for x in list(sys.stdin.readlines())]

        for idx, path in enumerate(all_files):
            (dirName, fname) = path.rsplit(os.path.sep, 1)
            if not os.path.exists(os.path.join(dirName, fname)):
                continue
            # Figure out what the memo key will be early
            basepath = self.rec_split(dirName)
            if len(basepath) == 0:
                memo_key = fname
            else:
                memo_key = os.path.join(os.path.join(*basepath), fname)

            # So that we can check if it really needs to be uploaded.
            already_uploaded = memo_key in self.memo_path.keys()
            fid = self.memoized_path(basepath, base_folder=self.folder_id)
            print('[%s/%s] %s/%s uploaded=%' % (idx + 1, len(all_files), fid, fname, already_uploaded))

            if not already_uploaded:
                if self.non_local:
                    self.gi.libraries.upload_file_from_local_path(
                        self.library_id,
                        os.path.join(dirName, fname),
                        folder_id=fid,
                    )
                else:
                    self.gi.libraries.upload_from_galaxy_filesystem(
                        self.library_id,
                        os.path.join(dirName, fname),
                        folder_id=fid,
                        link_data_only='link_to_files' if self.should_link else 'copy_files',
                    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Upload a directory into a data library')
    parser.add_argument( "-u", "--url", dest="url", required=True, help="Galaxy URL" )
    parser.add_argument( "-a", "--api", dest="api", required=True, help="API Key" )

    parser.add_argument( "-l", "--lib", dest="library_id", required=True, help="Library ID" )
    parser.add_argument( "-f", "--folder", dest="folder_id", help="Folder ID. If not specified, will go to root of library." )

    parser.add_argument( "--nonlocal", dest="non_local", action="store_true", default=False,
                        help="Set this flag if you are NOT running this script on your Galaxy head node with access to the full filesystem" )
    parser.add_argument( "--link", dest="should_link", action="store_true", default=False,
                        help="Link datasets only, do not upload to Galaxy. ONLY Avaialble if you run 'locally' relative to your Galaxy head node/filesystem ")
    args = parser.parse_args()

    u = Uploader(**vars(args))
    u.upload()
