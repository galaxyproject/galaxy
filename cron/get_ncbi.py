import urllib, pkg_resources, os
pkg_resources.require( 'elementtree' )
from elementtree import ElementTree, ElementInclude
from xml.parsers.expat import ExpatError as XMLParseErrorThing
import sys

import pkg_resources

class GetListing:
    def __init__( self, data ):
        self.tree = ElementTree.parse( data )
        self.root = self.tree.getroot()
        ElementInclude.include(self.root)
        
    def xml_text(self, name=None):
        """Returns the text inside an element"""
        root = self.root
        if name is not None:
            # Try attribute first
            val = root.get(name)
            if val:
                return val
            # Then try as element
            elem = root.find(name)
        else:
            elem = root
        if elem is not None and elem.text:
            text = ''.join(elem.text.splitlines())
            return text.strip()
        # No luck, return empty string
        return ''

def dlcachefile( webenv, querykey, i, results ):
    url = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=nuccore&usehistory=y&term=nuccore_assembly[filter]%20AND%20refseq[filter]'
    fp = urllib.urlopen( url )
    search = GetListing( fp )
    fp.close()
    webenv = search.xml_text( 'WebEnv' )
    querykey = search.xml_text( 'QueryKey' )
    url = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=nuccore&WebEnv=%s&query_key=%s&retstart=%d&retmax=%d' % ( webenv, querykey, i, results )
    fp = urllib.urlopen( url )
    cachefile = os.tmpfile()
    for line in fp:
        cachefile.write( line )
    fp.close()
    cachefile.flush()
    cachefile.seek(0)
    return cachefile
    

url = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=nuccore&usehistory=y&term=nuccore_assembly[filter]%20AND%20refseq[filter]'
fp = urllib.urlopen( url )
results = GetListing( fp )
fp.close()

webenv = results.xml_text( 'WebEnv' )
querykey = results.xml_text( 'QueryKey' )
counts = int( results.xml_text( 'Count' ) )
results = 10000
found = 0

for i in range(0, counts + results, results):
    rets = dict()
    cache = dlcachefile( webenv, querykey, i, results )
    try:
        xmldoc = GetListing( cache )
    except (IOError, XMLParseErrorThing):
        cache = dlcachefile( webenv, querykey, i, results )
        try:
            xmldoc = GetListing( cache )
        except (IOError, XMLParseErrorThing):
            cache.close()
            exit()
        pass
    finally:
        cache.close()
    entries = xmldoc.root.findall( 'DocSum' )
    for entry in entries:
        dbkey = None
        children = entry.findall('Item')
        for item in children:
            rets[ item.get('Name') ] = item.text
        if not rets['Caption'].startswith('NC_'):
            continue
            
        for ret in rets['Extra'].split('|'):
            if not ret.startswith('NC_'):
                continue
            else:
                dbkey = ret
                break
        if dbkey is not None:
            print '\t'.join( [ dbkey, rets['Title'] ] )
