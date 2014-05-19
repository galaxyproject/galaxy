import logging
import os
import tool_shed.util.shed_util_common as suc
from tool_shed.util import hg_util
from galaxy.web.form_builder import SelectField
from galaxy.util.bunch import Bunch

log = logging.getLogger( __name__ )


class RepositoryGridFilterManager( object ):
    """Provides filtered views of the many Tool SHed repository grids."""

    filters = Bunch( CERTIFIED_LEVEL_ONE = 'certified_level_one',
                     CERTIFIED_LEVEL_TWO = 'certified_level_two',
                     CERTIFIED_LEVEL_ONE_SUITES = 'certified_level_one_suites',
                     CERTIFIED_LEVEL_TWO_SUITES = 'certified_level_two_suites' )

    def get_grid_title( self, trans, trailing_string='', default='' ):
        filter = self.get_filter( trans )
        if filter == self.filters.CERTIFIED_LEVEL_ONE:
            return "Certified 1 Repositories %s" % trailing_string
        if filter == self.filters.CERTIFIED_LEVEL_TWO:
            return "Certified 2 Repositories %s" % trailing_string
        if filter == self.filters.CERTIFIED_LEVEL_ONE_SUITES:
            return "Certified 1 Repository Suites %s" % trailing_string
        if filter == self.filters.CERTIFIED_LEVEL_TWO_SUITES:
            return "Certified 2 Repository Suites %s" % trailing_string
        return "%s" % default

    def get_filter( self, trans ):
        filter = trans.get_cookie( name='toolshedrepogridfilter' )
        return filter or None

    def is_valid_filter( self, filter ):
        if filter is None:
            return True
        for valid_key, valid_filter in self.filters.items():
            if filter == valid_filter:
                return True
        return False

    def set_filter( self, trans, **kwd ):
        # Set a session cookie value with the selected filter.
        filter = kwd.get( 'filter', None )
        if filter is not None and self.is_valid_filter( filter ):
            trans.set_cookie( value=filter, name='toolshedrepogridfilter' )
        # if the filter is not valid, expire the cookie.
        trans.set_cookie( value=filter,name='toolshedrepogridfilter', age=-1 )

def build_approved_select_field( trans, name, selected_value=None, for_component=True ):
    options = [ ( 'No', trans.model.ComponentReview.approved_states.NO ),
                ( 'Yes', trans.model.ComponentReview.approved_states.YES ) ]
    if for_component:
        options.append( ( 'Not applicable', trans.model.ComponentReview.approved_states.NA ) )
        if selected_value is None:
            selected_value = trans.model.ComponentReview.approved_states.NA
    select_field = SelectField( name=name )
    for option_tup in options:
        selected = selected_value and option_tup[ 1 ] == selected_value
        select_field.add_option( option_tup[ 0 ], option_tup[ 1 ], selected=selected )
    return select_field

def build_changeset_revision_select_field( trans, repository, selected_value=None, add_id_to_name=True,
                                           downloadable=False, reviewed=False, not_reviewed=False ):
    """
    Build a SelectField whose options are the changeset_rev strings of certain revisions of the
    received repository.
    """
    options = []
    changeset_tups = []
    refresh_on_change_values = []
    if downloadable:
        # Restrict the options to downloadable revisions.
        repository_metadata_revisions = repository.downloadable_revisions
    elif reviewed:
        # Restrict the options to revisions that have been reviewed.
        repository_metadata_revisions = []
        metadata_changeset_revision_hashes = []
        for metadata_revision in repository.metadata_revisions:
            metadata_changeset_revision_hashes.append( metadata_revision.changeset_revision )
        for review in repository.reviews:
            if review.changeset_revision in metadata_changeset_revision_hashes:
                repository_metadata_revisions.append( review.repository_metadata )
    elif not_reviewed:
        # Restrict the options to revisions that have not yet been reviewed.
        repository_metadata_revisions = []
        reviewed_metadata_changeset_revision_hashes = []
        for review in repository.reviews:
            reviewed_metadata_changeset_revision_hashes.append( review.changeset_revision )
        for metadata_revision in repository.metadata_revisions:
            if metadata_revision.changeset_revision not in reviewed_metadata_changeset_revision_hashes:
                repository_metadata_revisions.append( metadata_revision )
    else:
        # Restrict the options to all revisions that have associated metadata.
        repository_metadata_revisions = repository.metadata_revisions
    for repository_metadata in repository_metadata_revisions:
        rev, label, changeset_revision = \
            hg_util.get_rev_label_changeset_revision_from_repository_metadata( trans,
                                                                               repository_metadata,
                                                                               repository=repository,
                                                                               include_date=True,
                                                                               include_hash=False )
        changeset_tups.append( ( rev, label, changeset_revision ) )
        refresh_on_change_values.append( changeset_revision )
    # Sort options by the revision label.  Even though the downloadable_revisions query sorts by update_time,
    # the changeset revisions may not be sorted correctly because setting metadata over time will reset update_time.
    for changeset_tup in sorted( changeset_tups ):
        # Display the latest revision first.
        options.insert( 0, ( changeset_tup[ 1 ], changeset_tup[ 2 ] ) )
    if add_id_to_name:
        name = 'changeset_revision_%d' % repository.id
    else:
        name = 'changeset_revision'
    select_field = SelectField( name=name,
                                refresh_on_change=True,
                                refresh_on_change_values=refresh_on_change_values )
    for option_tup in options:
        selected = selected_value and option_tup[ 1 ] == selected_value
        select_field.add_option( option_tup[ 0 ], option_tup[ 1 ], selected=selected )
    return select_field
