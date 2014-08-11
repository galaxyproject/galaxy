"""
Functionality for dealing with build sites for legacy display applications.
"""
import os.path


class BuildSites( object ):

    def __init__( self, app ):
        self._app = app
        self._build_sites = {}
        self.load_build_sites()

    def read_build_sites( self, filename, check_builds=True ):
        """ read db names to ucsc mappings from file, this file should probably be merged with the one above """
        build_sites = []
        try:
            for line in open(filename):
                try:
                    if line[0:1] == "#":
                        continue
                    fields = line.replace("\r", "").replace("\n", "").split("\t")
                    site_name = fields[0]
                    site = fields[1]
                    if check_builds:
                        site_builds = fields[2].split(",")
                        site_dict = {'name': site_name, 'url': site, 'builds': site_builds}
                    else:
                        site_dict = {'name': site_name, 'url': site}
                    build_sites.append( site_dict )
                except:
                    continue
        except:
            print "ERROR: Unable to read builds for site file %s" % filename
        return build_sites

    def load_build_sites( self ):
        self._build_sites['ucsc'] = self.read_build_sites( self._app.config.ucsc_build_sites )
        self._build_sites['gbrowse'] = self.read_build_sites( self._app.config.gbrowse_build_sites )

    def _get_site_by_build( self, site_type, build ):
        sites = []
        for site in self._build_sites[site_type]:
            if build in site['builds']:
                sites.append((site['name'], site['url']))
        return sites

    def get_ucsc_sites_by_build( self, build ):
        return self._get_site_by_build( 'ucsc', build )

    def get_gbrowse_sites_by_build( self, build ):
        return self._get_site_by_build( 'gbrowse', build )
