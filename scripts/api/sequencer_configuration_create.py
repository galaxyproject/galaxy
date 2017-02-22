#!/usr/bin/env python
from __future__ import print_function

import os
import sys

from common import get, submit


def create_sequencer_configuration( key, base_url, request_form_filename, sample_form_filename, request_type_filename, email_addresses, return_formatted=True ):
    # create request_form
    data = {}
    data[ 'xml_text' ] = open( request_form_filename ).read()
    request_form = submit( key, "%sforms" % base_url, data, return_formatted=False )[0]
    # create sample_form
    data = {}
    data[ 'xml_text' ] = open( sample_form_filename ).read()
    sample_form = submit( key, "%sforms" % base_url, data, return_formatted=False )[0]
    # get user ids
    user_ids = [ user['id'] for user in get( key, "%susers" % base_url ) if user['email'] in email_addresses ]
    # create role, assign to user
    data = {}
    data[ 'name' ] = "request_type_role_%s_%s_%s name" % ( request_form['id'], sample_form['id'], '_'.join( email_addresses ) )
    data[ 'description' ] = "request_type_role_%s_%s_%s description" % ( request_form['id'], sample_form['id'], '_'.join( email_addresses ) )
    data[ 'user_ids' ] = user_ids
    role_ids = [ role[ 'id' ] for role in submit( key, "%sroles" % base_url, data, return_formatted=False ) ]
    # create request_type
    data = {}
    data[ 'request_form_id' ] = request_form[ 'id' ]
    data[ 'sample_form_id' ] = sample_form[ 'id' ]
    data[ 'role_ids' ] = role_ids
    data[ 'xml_text' ] = open( request_type_filename ).read()
    return submit( key, "%srequest_types" % base_url, data, return_formatted=return_formatted )  # create and print out results for request type


def main():
    try:
        key = sys.argv[1]
        base_url = sys.argv[2]
        request_form_filename = sys.argv[3]
        sample_form_filename = sys.argv[4]
        request_type_filename = sys.argv[5]
        email_addresses = sys.argv[6].split( ',' )
    except IndexError:
        print('usage: %s key base_url request_form_xml_description_file sample_form_xml_description_file request_type_xml_description_file email_address1[,email_address2]' % os.path.basename( sys.argv[0] ))
        sys.exit( 1 )
    return create_sequencer_configuration( key, base_url, request_form_filename, sample_form_filename, request_type_filename, email_addresses, return_formatted=True )


if __name__ == "__main__":
    main()
