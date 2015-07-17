var webpack = require( 'webpack' ),
    // paths
    path = require( 'path' ),
    scriptsBase = path.join( __dirname, 'galaxy/scripts' ),
    libsBase = path.join( scriptsBase, 'libs' ),
    // chunks
    CommonsChunkPlugin = new webpack.optimize.CommonsChunkPlugin( 'common.js' );


module.exports = {
    entry   : {
        libs        : './galaxy/scripts/apps/libs.js',
        history     : './galaxy/scripts/apps/history-app.js'
    },
    output  : {
        path        : '../static/scripts/bundled',
        filename    : '[name].bundled.js'
    },
    resolve : {
        alias : {
            //TODO: correct our imports and remove these rules
            // Backbone looks for these in the same directory
            jquery      : path.join( libsBase, 'jquery/jquery' ),
            underscore  : path.join( libsBase, 'underscore.js' ),
            // requirejs' i18n doesn't play well with webpack
            // note: strangely, order does matter here - this must come before utils below
            'utils/localization' : path.join( scriptsBase, 'utils/webpack-localization' ),
            // aliases/shims for existing AMD requires
            utils       : path.join( scriptsBase, 'utils' ),
            ui          : path.join( scriptsBase, 'ui' ),
            mvc         : path.join( scriptsBase, 'mvc' ),

            'galaxy.masthead' : path.join( scriptsBase, 'galaxy.masthead' )
        }
    },
    plugins : [
        CommonsChunkPlugin
    ]
};
