"""Classes to generate links for old-style display applications.

Separating Transaction based elements of display applications from datatypes.
"""

#FIXME: The code contained within this file is for old-style display applications, but
#this module namespace is intended to only handle the new-style display applications.

import urllib

# for the url_for hack
import pkg_resources
pkg_resources.require( "Routes" )
import routes

from galaxy import util
from galaxy.web import url_for
from galaxy.datatypes.interval import Interval, Gff, Wiggle, CustomTrack

#TODO: Ideally, these classes would be instantiated in the trans (or some other semi-persistant fixture)
#   Currently, these are instantiated per HDA which is not the best solution

#TODO: these could be extended to handle file_function and parse/contain the builds.txt files

#HACK: these duplicate functionality from the individual datatype classes themselves

def get_display_app_link_generator( display_app_name ):
    """Returns an instance of the proper link generator class
    based on the display_app_name or DisplayAppLinkGenerator
    if the display_app_name is unrecognized.
    """
    if display_app_name == 'ucsc':
        return UCSCDisplayAppLinkGenerator()

    elif display_app_name == 'gbrowse':
        return GBrowseDisplayAppLinkGenerator()

    return DisplayAppLinkGenerator()


class DisplayAppLinkGenerator( object ):
    """Base class for display application link generators.

    This class returns an empty list of links for all datatypes.
    """
    def __init__( self ):
        self.display_app_name = ''

    def no_links_available( self, dataset, app, base_url, url_for=url_for ):
        """Called when no display application links are available
        for this display app name and datatype combination.
        """
        return []

    def _link_function_from_datatype( self, datatype ):
        """Dispatch to proper link generating function on datatype.
        """
        return self.no_links_available

    def generate_links( self, trans, dataset ):
        # here's the hack - which is expensive (time)
        web_url_for = routes.URLGenerator( trans.webapp.mapper, trans.environ )

        link_function = self._link_function_from_datatype( dataset.datatype )
        display_links = link_function( dataset, trans.app, trans.request.base, url_for=web_url_for )

        return display_links


class UCSCDisplayAppLinkGenerator( DisplayAppLinkGenerator ):
    """Class for generating links to display data in the
    UCSC genome browser.

    This class returns links for the following datatypes and their subclasses:
        Interval, Wiggle, Gff, CustomTrack
    """
    def __init__( self ):
        self.display_app_name = 'ucsc'

    def _link_function_from_datatype( self, datatype ):
        """Dispatch to proper link generating function based on datatype.
        """
        if( ( isinstance( datatype, Interval ) )
        or  ( isinstance( datatype, Wiggle ) )
        or  ( isinstance( datatype, Gff ) )
        or  ( isinstance( datatype, CustomTrack ) ) ):
            return self.ucsc_links
        else:
            return super( UCSCDisplayAppLinkGenerator, self )._link_function_from_datatype( datatype )

    def ucsc_links( self, dataset, app, base_url, url_for=url_for ):
        """Generate links to UCSC genome browser sites based on the dbkey
        and content of dataset.
        """
        # this is a refactor of Interval.ucsc_links, GFF.ucsc_links, Wiggle.ucsc_links, and CustomTrack.ucsc_links
        #TODO: app vars can be moved into init (and base_url as well)
        chrom, start, stop = dataset.datatype.get_estimated_display_viewport( dataset )
        if chrom is None:
            return []
        ret_val = []
        for site_name, site_url in util.get_ucsc_by_build(dataset.dbkey):
            if site_name in app.config.ucsc_display_sites:
                internal_url = url_for( controller='dataset', dataset_id=dataset.id,
                                        action='display_at', filename='%s_%s' % ( self.display_app_name, site_name ) )
                base_url = app.config.get( "display_at_callback", base_url )
                display_url = urllib.quote_plus( "%s%s/display_as?id=%i&display_app=%s&authz_method=display_at"
                        % (base_url, url_for( controller='root' ), dataset.id, self.display_app_name) )
                redirect_url = urllib.quote_plus( "%sdb=%s&position=%s:%s-%s&hgt.customText=%%s"
                        % (site_url, dataset.dbkey, chrom, start, stop ) )

                link = '%s?redirect_url=%s&display_url=%s' % ( internal_url, redirect_url, display_url )
                ret_val.append( ( site_name, link ) )

        return ret_val


class GBrowseDisplayAppLinkGenerator( DisplayAppLinkGenerator ):
    """Class for generating links to display data in the
    GBrowse genome browser.

    This class returns links for the following datatypes and their subclasses:
        Gff, Wiggle
    """
    def __init__( self ):
        self.display_app_name = 'gbrowse'

    def _link_function_from_datatype( self, datatype ):
        """Dispatch to proper link generating function based on datatype.
        """
        if( ( isinstance( datatype, Gff ) )
        or  ( isinstance( datatype, Wiggle ) ) ):
            return self.gbrowse_links
        else:
            return super( GBrowseDisplayAppLinkGenerator, self )._link_function_from_datatype( datatype )

    def gbrowse_links( self, dataset, app, base_url, url_for=url_for ):
        """Generate links to GBrowse genome browser sites based on the dbkey
        and content of dataset.
        """
        # when normalized for var names, Gff.gbrowse_links and Wiggle.gbrowse_links are the same
        # also: almost identical to ucsc_links except for the 'chr' stripping, sites_by_build, config key
        #   could be refactored even more
        chrom, start, stop = dataset.datatype.get_estimated_display_viewport( dataset )
        if chrom is None:
            return []
        ret_val = []
        for site_name, site_url in util.get_gbrowse_sites_by_build( dataset.dbkey ):
            if site_name in app.config.gbrowse_display_sites:
                # strip chr from seqid
                if chrom.startswith( 'chr' ) and len ( chrom ) > 3:
                    chrom = chrom[3:]
                internal_url = url_for( controller='dataset', dataset_id=dataset.id,
                                        action='display_at', filename='%s_%s' % ( self.display_app_name, site_name ) )
                redirect_url = urllib.quote_plus( "%s/?q=%s:%s..%s&eurl=%%s" % ( site_url, chrom, start, stop ) )
                base_url = app.config.get( "display_at_callback", base_url )
                display_url = urllib.quote_plus( "%s%s/display_as?id=%i&display_app=%s&authz_method=display_at"
                    % ( base_url, url_for( controller='root' ), dataset.id, self.display_app_name ) )
                link = '%s?redirect_url=%s&display_url=%s' % ( internal_url, redirect_url, display_url )
                ret_val.append( ( site_name, link ) )

        return ret_val
