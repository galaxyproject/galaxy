define( [ 'utilities/utils', "plugins/ngl/viewer" ], function( Utils, ngl ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            var dataset = options.dataset,
                settings = options.chart.settings,
                url = window.location.protocol + '//' + window.location.host + "/datasets/" + dataset.dataset_id +
                      "/display?to_ext=" + dataset.extension,
                stage = new ngl.Stage( options.targets[ 0 ], { backgroundColor: settings.get( 'backcolor' ) } );
            Utils.get( {
                url     : url,
                cache   : true,
                success : function( response ) {
                    var viewer_options = {},
                        representation_parameters = {};
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
                    stage.loadFile( url, {ext: dataset.extension, name: dataset.name, defaultRepresentation: true} ).then( function( o ) {
                        o.addRepresentation( viewer_options.mode, representation_parameters );
                        o.centerView();
                    } );
                    stage.setQuality( settings.get( 'quality' ) );
                    if( settings.get( 'spin' ) === true || settings.get( 'spin' ) === 'true' ) {
                        stage.setSpin( [ 0, 1, 0 ], 0.01 );
                    }
                    options.chart.state( 'ok', 'Chart drawn.' );
                    options.process.resolve();
                },
                error   : function() {
                    options.chart.state( 'ok', 'Failed to load pdb file.' );
                    options.process.resolve();
                }
            });
            // Re-renders the molecule view when window is resized
            $( window ).resize( function() { stage.viewer.handleResize() } );
        }
    });
});
