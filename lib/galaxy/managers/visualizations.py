"""
Manager and Serializers for Visualizations.

Visualizations are saved configurations/variables used to
reproduce a specific view in a Galaxy visualization.
"""

from galaxy import exceptions
from galaxy import model
import galaxy.web

from galaxy.managers import base
from galaxy.managers import sharable

import logging
log = logging.getLogger( __name__ )


# =============================================================================
class VisualizationManager( sharable.SharableModelManager ):
    """
    """

    model_class = model.Visualization
    default_order_by = ( model.Visualization.create_time, )
    foreign_key_name = 'visualization'
    user_share_model = model.VisualizationUserShareAssociation

    tag_assoc = model.VisualizationTagAssociation
    annotation_assoc = model.VisualizationAnnotationAssociation
    rating_assoc = model.VisualizationRatingAssociation

    def __init__( self, app, *args, **kwargs ):
        """
        """
        super( VisualizationManager, self ).__init__( app, *args, **kwargs )

    def copy( self, trans, visualization, user, **kwargs ):
        """
        """
        pass

    #TODO: revisions


## =============================================================================
class VisualizationSerializer( sharable.SharableModelSerializer ):
    """
    Interface/service object for serializing visualizations into dictionaries.
    """

    def __init__( self, app ):
        super( VisualizationSerializer, self ).__init__( app )
        self.visualizations_manager = VisualizationManager( app )

        summary_view = [
        ]
        # in the Visualizations' case, each of these views includes the keys from the previous
        detailed_view = summary_view + [
        ]
        self.serializable_keys = detailed_view + []
        self.views = {
            'summary'   : summary_view,
            'detailed'  : detailed_view
        }
        self.default_view = 'summary'

    def add_serializers( self ):
        super( VisualizationSerializer, self ).add_serializers()
        self.serializers.update({
        })


# =============================================================================
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
        self.deserializable_keys = self.deserializers.keys()
