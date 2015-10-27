var webpack = require( 'webpack' ),
    // paths
    path = require( 'path' ),
    scriptsBase = path.join( __dirname, 'galaxy/scripts' ),
    libsBase = path.join( scriptsBase, 'libs' ),
    // chunks
    CommonsChunkPlugin = new webpack.optimize.CommonsChunkPlugin( 'common.js' );


module.exports = {
    devtool : 'source-map',
    entry   : {
        galaxy      : './galaxy/scripts/apps/galaxy.js',
        // remove when these are no longer needed from any pages
        libs        : './galaxy/scripts/apps/libs.js',
        analysis    : './galaxy/scripts/apps/analysis.js',
        history     : './galaxy/scripts/apps/history-app.js'
    },
    output  : {
        path        : '../static/scripts/bundled',
        filename    : '[name].bundled.js'
    },
    resolve : {
        root  : scriptsBase,
        alias : {
            //TODO: correct our imports and remove these rules
            // Backbone looks for these in the same directory
            jquery      : path.join( libsBase, 'jquery/jquery' ),
            underscore  : path.join( libsBase, 'underscore.js' ),
            // we import these (for now) from the libs dir
            'libs/underscore'       : path.join( libsBase, 'underscore.js' ),
            'libs/backbone/backbone': path.join( libsBase, 'backbone/backbone.js' ),
            // requirejs' i18n doesn't play well with webpack
            // note: strangely, order does matter here - this must come before utils below
            'utils/localization' : path.join( scriptsBase, 'utils/webpack-localization' ),
        }
    },
    plugins : [
        CommonsChunkPlugin
    ]
};
