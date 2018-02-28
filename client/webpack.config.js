var webpack = require("webpack");

var path = require("path");
var scriptsBase = path.join(__dirname, "galaxy/scripts");
var libsBase = path.join(scriptsBase, "libs");

const VueLoaderPlugin = require('vue-loader/lib/plugin');

// libraries used on almost every page
var commonLibs = [
    "polyfills",
    // jquery et al
    "jquery",
    "libs/jquery/jquery.migrate",
    "libs/jquery/jquery.autocomplete",
    "libs/jquery/jquery.event.hover",
    "libs/jquery/jquery.event.drag",
    "libs/jquery/jquery.mousewheel",
    "libs/jquery/jquery.form",
    "libs/jquery/jquery.rating",
    "libs/jquery/select2",
    "libs/jquery.sparklines",
    "libs/jquery/jquery-ui",
    "libs/jquery/jstorage",
    "libs/jquery/jquery.complexify",
    "libs/farbtastic",
    "bootstrap",
    "bootstrap-tour",
    "vue",
    // mvc
    "libs/underscore",
    "libs/backbone",
    "libs/toastr",
    // all pages get these
    "ui/autocom_tagging",
    "layout/modal",
    "layout/panel",
    "onload"
];

let buildconfig = {
    entry: {
        libs: commonLibs,
        login: "./galaxy/scripts/apps/login.js",
        analysis: "./galaxy/scripts/apps/analysis.js",
        admin: "./galaxy/scripts/apps/admin.js",
        chart: "./galaxy/scripts/apps/chart.js",
        extended: "./galaxy/scripts/apps/extended.js"
    },
    output: {
        path: path.join(__dirname, "../", "static/scripts/bundled"),
        filename: "[name].bundled.js"
    },
    resolve: {
        modules: [scriptsBase, "node_modules"],
        alias: {
            //TODO: correct our imports and remove these rules
            // Backbone looks for these in the same root directory
            jquery: path.join(libsBase, "jquery/jquery"),
            underscore: path.join(libsBase, "underscore.js")
        }
    },
    module: {
        rules: [
            {
                test: /\.vue$/,
                loader: "vue-loader",
                options: {
                    loaders: {
                        js: "babel-loader"
                    }
                }
            },
            {
                test: /\.js$/,
                exclude: [/(node_modules\/(?!(handsontable)\/)|bower_components)/, libsBase],
                loader: "babel-loader"
            },
            {
                test: require.resolve("jquery"),
                use: [
                    {
                        loader: "expose-loader",
                        options: "jQuery"
                    },
                    {
                        loader: "expose-loader",
                        options: "$"
                    }
                ]
            },
            {
                test: /\.css$/,
                use: [
                    'style-loader',
                    'css-loader'
                ]
            },
            {
                test: /\.vue$/,
                loader: "vue-loader"
            }
        ]
    },
    node: {
        setImmediate: false
    },
    resolveLoader: {
        alias: {
            // since we support both requirejs i18n and non-requirejs and both use a similar syntax,
            // use an alias so we can just use one file
            i18n: "amdi18n-loader"
        }
    },
    plugins: [
        // this plugin allows using the following keys/globals in scripts (w/o req'ing them first)
        // and webpack will automagically require them in the bundle for you
        new webpack.ProvidePlugin({
            $: "jquery",
            jQuery: "jquery",
            "window.jQuery": "jquery",
            _: "underscore",
            Backbone: "libs/backbone"
        }),
        // new webpack.optimize.LimitChunkCountPlugin({ maxChunks: 1 })
        new VueLoaderPlugin()
    ]
};

if (process.env.GXY_BUILD_SOURCEMAPS || process.env.NODE_ENV == "development") {
    buildconfig.devtool = "source-map";
}

module.exports = buildconfig;
