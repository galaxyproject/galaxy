#======= XML helper methods ====================================================

import xml.dom.minidom

def get_value( dom, tag_name ):
    '''
    This method extracts the tag value from the xml message
    '''
    nodelist = dom.getElementsByTagName( tag_name )[ 0 ].childNodes
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc

def get_value_index( dom, tag_name, dataset_id ):
    '''
    This method extracts the tag value from the xml message
    '''
    try:
        nodelist = dom.getElementsByTagName( tag_name )[ dataset_id ].childNodes
    except:
        return None
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc