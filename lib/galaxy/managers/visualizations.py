"""
Manager and Serializers for Visualizations.

Visualizations are saved configurations/variables used to
reproduce a specific view in a Galaxy visualization.
"""

from galaxy import model
from galaxy.managers import sharable

import logging
log = logging.getLogger( __name__ )


class VisualizationManager( sharable.SharableModelManager ):
    """
    Handle operations outside and between visualizations and other models.
    """

    # TODO: revisions

    model_class = model.Visualization
    foreign_key_name = 'visualization'
    user_share_model = model.VisualizationUserShareAssociation

    tag_assoc = model.VisualizationTagAssociation
    annotation_assoc = model.VisualizationAnnotationAssociation
    rating_assoc = model.VisualizationRatingAssociation

    def __init__( self, app, *args, **kwargs ):
        """
        """
        super( VisualizationManager, self ).__init__( app, *args, **kwargs )

    # def copy( self, trans, visualization, user, **kwargs ):
    #    """
    #    """
    #    pass


class VisualizationSerializer( sharable.SharableModelSerializer ):
    """
    Interface/service object for serializing visualizations into dictionaries.
    """
    model_manager_class = VisualizationManager
    SINGLE_CHAR_ABBR = 'v'

    def __init__( self, app ):
        super( VisualizationSerializer, self ).__init__( app )
        self.visualization_manager = self.manager

        self.default_view = 'summary'
        self.add_view( 'summary', [] )
        self.add_view( 'detailed', [] )

    def add_serializers( self ):
        super( VisualizationSerializer, self ).add_serializers()
        self.serializers.update({
        })


class VisualizationDeserializer( sharable.SharableModelDeserializer ):
    """
    Interface/service object for validating and deserializing
    dictionaries into visualizations.
    """
    model_manager_class = VisualizationManager

    def __init__( self, app ):
        super( VisualizationDeserializer, self ).__init__( app )
        self.visualization_manager = self.manager

    def add_deserializers( self ):
        super( VisualizationDeserializer, self ).add_deserializers()
        self.deserializers.update({
        })
        self.deserializable_keyset.update( self.deserializers.keys() )
