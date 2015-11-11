var webpack = require( 'webpack' ),
    // paths
    path = require( 'path' ),
    scriptsBase = path.join( __dirname, 'galaxy/scripts' ),
    libsBase = path.join( scriptsBase, 'libs' ),
    // libraries used on almost every page
    // TODO: reduce
    commonLibs = [
        // jquery et al
        'jquery',
        'libs/jquery/jquery.migrate',
        // jquery plugins
        'libs/jquery/select2',
        'libs/jquery/jquery.event.hover',
        'libs/jquery/jquery.form',
        'libs/jquery/jquery.rating',
        'libs/jquery.sparklines',
        'libs/bootstrap',
        // mvc
        'libs/underscore',
        'libs/backbone',
        'libs/handlebars.runtime',
        // all pages get these
        'polyfills',
        'modal',
        'ui/autocom_tagging',
        'layout/panel',
        'onload',
    ];


module.exports = {
    devtool : 'source-map',
    entry   : {
        galaxy  : './galaxy/scripts/apps/galaxy.js',
        analysis: './galaxy/scripts/apps/analysis.js',
        libs    : commonLibs
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
            // requirejs' i18n doesn't play well with webpack
            // note: strangely, order does matter here - this must come before utils below
            'utils/localization' : path.join( scriptsBase, 'utils/webpack-localization' ),
        }
    },
    plugins : [
        new webpack.optimize.CommonsChunkPlugin( 'libs', 'libs.bundled.js' ),
        // this plugin allows using the following keys/globals in scripts (w/o req'ing them first)
        // and webpack will automagically require them in the bundle for you
        new webpack.ProvidePlugin({
            $:                  'jquery',
            jQuery:             'jquery',
            'window.jQuery':    'jquery',
            _:                  "underscore",
            Backbone:           'libs/backbone',
            Handlebars:         'libs/handlebars.runtime'
        }),
        // new webpack.optimize.LimitChunkCountPlugin({ maxChunks: 1 })
    ]
};
