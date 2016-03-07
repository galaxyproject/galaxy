#!/usr/bin/env python
import sys

from common import submit

usage = "USAGE: copy_hda_to_library_folder.py <base url> <api key> <hda id> <library id> <folder id> [ message ]"


def copy_hda_to_library_folder( base_url, key, hda_id, library_id, folder_id, message='' ):
    url = 'http://%s/api/libraries/%s/contents' % ( base_url, library_id )
    payload = {
        'folder_id'     : folder_id,
        'create_type'   : 'file',
        'from_hda_id'   : hda_id,
    }
    if message:
        payload.update( dict( ldda_message=message ) )

    return submit( key, url, payload )


if __name__ == '__main__':
    num_args = len( sys.argv )
    if num_args < 6:
        print >> sys.stderr, usage
        sys.exit( 1 )

    ( base_url, key, hda_id, library_id, folder_id ) = sys.argv[1:6]

    message = ''
    if num_args >= 7:
        message = sys.argv[6]

    print >> sys.stderr, base_url, key, hda_id, library_id, folder_id, message
    returned = copy_hda_to_library_folder( base_url, key, hda_id, library_id, folder_id, message )
