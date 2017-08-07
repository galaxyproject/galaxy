define( [ 'utilities/utils', "plugins/ngl/viewer" ], function( Utils, ngl ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            var dataset = options.dataset,
                settings = options.chart.settings,
                stage = new ngl.Stage( options.targets[ 0 ], { backgroundColor: settings.get( 'backcolor' ) } ),
                viewer_options = {},
                representation_parameters = {},
                stage_parameters = {};

            _.each( settings.attributes, function( value, key ) {
                if ( key.startsWith( 'viewer|' ) ) {
                    viewer_options[ key.replace( 'viewer|', '' ) ] = value;
                }
            } );
            representation_parameters = { 
                radius: settings.get( 'radius' ),
                scale: settings.get( 'scale' ),
                assembly: settings.get( 'assembly' ),
                color: settings.get( 'colorscheme' ),
                opacity: settings.get( 'opacity' )
            };
            stage_parameters = { ext: dataset.extension, defaultRepresentation: true };
            try {
                stage.loadFile( dataset.download_url, stage_parameters ).then( function( component ) {
                    component.addRepresentation( viewer_options.mode, representation_parameters );
                    options.chart.state( 'ok', 'Chart drawn.' );
                    options.process.resolve();
                } );
            } catch( e ) {
                options.chart.state( 'failed', 'Could not load PDB file.' );
                options.process.resolve();
            }
            stage.setQuality( settings.get( 'quality' ) );
            if( settings.get( 'spin' ) === true || settings.get( 'spin' ) === 'true' ) {
                stage.setSpin( [ 0, 1, 0 ], 0.01 );
            }
            // Re-renders the molecule view when window is resized
            $( window ).resize( function() { stage.viewer.handleResize() } );
        }
    });
});
