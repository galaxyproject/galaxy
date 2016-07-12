var webpack = require( 'webpack' ),
    // paths
    path = require( 'path' ),
    scriptsBase = path.join( __dirname, 'galaxy/scripts' ),
    libsBase = path.join( scriptsBase, 'libs' ),

    // libraries used on almost every page
    // TODO: reduce
    commonLibs = [
        'polyfills',
        // jquery et al
        'jquery',
        'libs/jquery/jquery.migrate',
        // jquery plugins
        'libs/jquery/select2',
        'libs/jquery/jquery.event.hover',
        'libs/jquery/jquery.form',
        'libs/jquery/jquery.rating',
        'libs/jquery.sparklines',
        'libs/jquery/jquery-ui',
        'libs/bootstrap',
        'libs/bootstrap-tour',
        'libs/jquery.complexify',
        // mvc
        'libs/underscore',
        'libs/backbone',
        // all pages get these
        'ui/autocom_tagging',
        'layout/modal',
        'layout/panel',
        'onload',
    ];


module.exports = {
    devtool : 'source-map',
    entry   : {
        libs    : commonLibs,
        login   : './galaxy/scripts/apps/login.js',
        analysis: './galaxy/scripts/apps/analysis.js',
    },
    output  : {
        path        : '../static/scripts/bundled',
        filename    : '[name].bundled.js'
    },
    resolve : {
        root  : scriptsBase,
        alias : {
            //TODO: correct our imports and remove these rules
            // Backbone looks for these in the same root directory
            jquery      : path.join( libsBase, 'jquery/jquery' ),
            underscore  : path.join( libsBase, 'underscore.js' ),
        }
    },
    module : {
        loaders : [
        ],
    },
    resolveLoader : {
        alias : {
            // since we support both requirejs i18n and non-requirejs and both use a similar syntax,
            // use an alias so we can just use one file
            i18n : 'amdi18n'
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
        }),
        // new webpack.optimize.LimitChunkCountPlugin({ maxChunks: 1 })
    ],
};
