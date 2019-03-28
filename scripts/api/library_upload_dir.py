#!/usr/bin/env python
from __future__ import print_function

import argparse
import os
import sys
import textwrap

from bioblend import galaxy


class Uploader(object):

    def __init__(self, url, api, library_id, library_name, folder_id, folder_name,
                 should_link, non_local, dbkey, preserve_dirs,
                 tag_using_filenames, description, paths):
        """
        initialize uploader

        url Galaxy URL
        api API key to use
        library_id id of the library
        library_name name of the library
        folder_id id of the folder to upload to (None: root folder of the library)
        folder_name path in the Galaxy library where the files should be uploaded to 
        should_link link data sets instead of uploading 
        non_local set to true iff not running on Galaxy head node
        dbkey data base key (aka genome build)
        preserve_dirs preserve directory structure (boolean)
        tag_using_filenames tag data sets using file name
        description description of the topmost of the created folders
        paths list of paths to upload if empty will be read from stdin
        """
        self.gi = galaxy.GalaxyInstance(url=url, key=api)
        libs = self.gi.libraries.get_libraries(library_id=library_id,
                                        name=library_name)

        # TODO libs also contains deleted libraries even if it should not
        # https://github.com/galaxyproject/bioblend/issues/239 fixed by
        # https://github.com/galaxyproject/bioblend/pull/273
        # remove if bioblend>0.12 is released
        libs = [d for d in libs if not d['deleted']]

        if len(libs) == 0:
            raise Exception("Unknown library [%s,%s]" % (library_id, library_name))
        elif len(libs) > 1:
            raise Exception("Ambiguous libraries for [%s,%s]: %s" % (library_id, library_name, libs))
        else:
            libs = libs[0]
        self.library_id = libs['id']
        
        # set folder_id to root folder 
        # - will be overwritten if folder_id or folder_name != None
        # - needs to be done after prepopulate_memo
        self.folder_id = libs['root_folder_id']
        self.should_link = should_link
        self.non_local = non_local
        self.dbkey = dbkey
        self.preserve_dirs = preserve_dirs
        self.tag_using_filenames = tag_using_filenames
        self.description = description
        self.paths = paths
        # name -> id map for all folders 'below' folder_id
        self.memo_path = {}
        self.prepopulate_memo()
        # now really init the folder_id if folder_id or folder_name != None
        if folder_id:
            self.folder_id = folder_id
        elif folder_name:
            self.folder_id = self.memoized_path(self.rec_split(folder_name), base_folder=None)

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
            return self.memo_path[fk]
        else:
            for i in reversed(range(len(path_parts))):
                fk = '/'.join(path_parts[0:i + 1])
                if fk in self.memo_path:
                    dropped_prefix = path_parts[0:i + 1]
                    path_parts = path_parts[i + 1:]
                    base_folder = self.memo_path[fk]
                    break

        nfk = []
        for i in range(len(path_parts)):
            nfk.append('/'.join(list(dropped_prefix) + list(path_parts[0:i + 1])))

        # Recursively create the path from our base_folder starting points,
        # getting the IDs of each folder per path component
        ids = self.recursively_build_path(path_parts, base_folder, description=self.description)

        # These are then associated with the paths.
        for (key, fid) in zip(nfk, ids):
            self.memo_path[key] = fid
        return ids[-1]

    def recursively_build_path(self, path_parts, parent_folder_id, ids=None, description=""):
        """Given an iterable of path components and a parent folder id, recursively
        create directories below parent_folder_id"""
        if ids is None:
            ids = []
        if len(path_parts) == 0:
            return ids
        else:
            pf = self.gi.libraries.create_folder(self.library_id, path_parts[0], base_folder_id=parent_folder_id, description=description)
            ids.append(pf[0]['id'])
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
        if len(self.paths) == 0:
            all_files = [x.strip() for x in list(sys.stdin.readlines())]
        else:
            all_files = self.paths

        for idx, path in enumerate(all_files):
            if not os.path.exists(path):
                raise Exception("no such file or directory %s" %(path))
                continue
            (dirName, fname) = path.rsplit(os.path.sep, 1)
            # Figure out what the memo key will be early
            basepath = self.rec_split(dirName)
            if len(basepath) == 0:
                memo_key = fname
            else:
                memo_key = os.path.join(os.path.join(*basepath), fname)

            # So that we can check if it really needs to be uploaded.
            already_uploaded = memo_key in self.memo_path.keys()
            fid = self.memoized_path(basepath, base_folder=self.folder_id)
            print('[%s/%s] %s/%s uploaded=%s' % (idx + 1, len(all_files), fid, fname, already_uploaded))

            if not already_uploaded:
                if self.non_local:
                    self.gi.libraries.upload_file_from_local_path(
                        library_id=self.library_id,
                        file_local_path=path,
                        folder_id=fid,
                        dbkey=self.dbkey
                    )
                else:
                    self.gi.libraries.upload_from_galaxy_filesystem(
                        library_id=self.library_id,
                        filesystem_paths=path,
                        folder_id=fid,
                        dbkey=self.dbkey,
                        link_data_only='link_to_files' if self.should_link else 'copy_files',
                        preserve_dirs=self.preserve_dirs,
                        tag_using_filenames=self.tag_using_filenames
                    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''
        Takes one or more path given as positional arguments (or via stdin) and uploads |
        the files or directories contained therein into a data library.

        The contents of path (PATH/TO/FILE_OR_DIR) will be uploaded to
        PATH/TO/FILE_OR_DIR in the specified folder (-f/-F) and libary (-l/-L). Note that
        the path can be given relative to the current working directory. Data sets and
        folders will only be created in the library if they are not present yet. If
        --preserve_dirs is set then the structure in PATH/TO/FILE_OR_DIR will be preserved
        in the libary.'''))

    parser.add_argument("-u", "--url", dest="url", required=True, help="Galaxy URL")
    parser.add_argument("-a", "--api", dest="api", required=True, help="API Key")

    libparser = parser.add_mutually_exclusive_group(required=True)
    libparser.add_argument("-l", "--lib", dest="library_id", help="Library ID")
    libparser.add_argument("-L", "--library_name", help="Library name")
    folderparser = parser.add_mutually_exclusive_group(required=False)
    folderparser.add_argument("-f", "--folder", dest="folder_id",
                        help="Folder ID. If not specified upload to root folder of the library or the folder specified with --folder_name.")
    folderparser.add_argument("-F", "--folder_name", help="Folder to upload to, can be a path")

    parser.add_argument("--nonlocal", dest="non_local", action="store_true", default=False,
                        help="Set this flag if you are NOT running this script on your Galaxy head node with access to the full filesystem")
    localparser = parser.add_argument_group('Options for local upload', 'options that only apply if --nonlocal is not set')
    localparser.add_argument("--link", dest="should_link", action="store_true", default=False,
                        help="Link datasets only, do not upload to Galaxy")
    localparser.add_argument("--preserve_dirs", action="store_true", default=False,
                        help="Preserve directory structure")
    localparser.add_argument("--tag_using_filenames", action="store_true", default=False,
                        help="Tag data sets with file name")
    parser.add_argument("--dbkey", default="?", help="Genome build")
    parser.add_argument("--description", default="", help="description for the topmost of the created folders")
    parser.add_argument('paths', nargs='*', help="path(s) to upload, will be read from stdin if not given")
    args = parser.parse_args()

    u = Uploader(**vars(args))
    u.upload()
