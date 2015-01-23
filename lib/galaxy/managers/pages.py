"""
Manager and Serializers for Pages.

Pages are markup created and saved by users that can contain Galaxy objects
(such as datasets) and are often used to describe or present an analysis
from within Galaxy.
"""

from galaxy import model
from galaxy.managers import sharable

import logging
log = logging.getLogger( __name__ )


class PageManager( sharable.SharableModelManager ):
    """
    """

    model_class = model.Page
    foreign_key_name = 'page'
    user_share_model = model.PageUserShareAssociation

    tag_assoc = model.PageTagAssociation
    annotation_assoc = model.PageAnnotationAssociation
    rating_assoc = model.PageRatingAssociation

    def __init__( self, app, *args, **kwargs ):
        """
        """
        super( PageManager, self ).__init__( app, *args, **kwargs )

    def copy( self, trans, page, user, **kwargs ):
        """
        """
        pass


class PageSerializer( sharable.SharableModelSerializer ):
    """
    Interface/service object for serializing pages into dictionaries.
    """
    SINGLE_CHAR_ABBR = 'p'

    def __init__( self, app ):
        super( PageSerializer, self ).__init__( app )
        self.page_manager = PageManager( app )

        summary_view = [
        ]
        # in the Pages' case, each of these views includes the keys from the previous
        detailed_view = summary_view + [
        ]
        self.serializable_keys = detailed_view + []
        self.views = {
            'summary': summary_view,
            'detailed': detailed_view
        }
        self.default_view = 'summary'

    def add_serializers( self ):
        super( PageSerializer, self ).add_serializers()
        self.serializers.update({
        })


class PageDeserializer( sharable.SharableModelDeserializer ):
    """
    Interface/service object for validating and deserializing dictionaries
    into pages.
    """
    model_manager_class = PageManager

    def __init__( self, app ):
        super( PageDeserializer, self ).__init__( app )
        self.page_manager = self.manager

    def add_deserializers( self ):
        super( PageDeserializer, self ).add_deserializers()
        self.deserializers.update({
        })
        self.deserializable_keys = self.deserializers.keys()
