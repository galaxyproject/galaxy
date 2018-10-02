/* eslint-env node */
const webpack = require("webpack");
const path = require("path");
const VueLoaderPlugin = require("vue-loader/lib/plugin");

const scriptsBase = path.join(__dirname, "galaxy/scripts");
const libsBase = path.join(scriptsBase, "libs");

// libraries used on almost every page
// var commonLibs = [
//     "polyfills",
//     // jquery et al
//     "jquery",
//     "libs/jquery/jquery.migrate",
//     "libs/jquery/jquery.autocomplete",
//     "libs/jquery/jquery.event.hover",
//     "libs/jquery/jquery.event.drag",
//     "libs/jquery/jquery.mousewheel",
//     "libs/jquery/jquery.form",
//     "libs/jquery/jquery.rating",
//     "libs/jquery/select2",
//     "libs/jquery.sparklines",
//     "libs/jquery/jquery-ui",
//     "libs/jquery/jstorage",
//     "libs/jquery/jquery.complexify",
//     "libs/farbtastic",
//     "bootstrap",
//     "bootstrap-tour",
//     "vue",
//     // mvc
//     "libs/underscore",
//     "libs/backbone",
//     "libs/toastr",
//     // all pages get these
//     "ui/autocom_tagging",
//     "layout/modal",
//     "layout/panel",
//     "onload"
// ];

let buildconfig = {
    entry: {
        login: ["polyfills", "onload", "./galaxy/scripts/apps/login.js"],
        analysis: ["polyfills", "onload", "./galaxy/scripts/apps/analysis.js"],
        admin: ["polyfills", "onload", "./galaxy/scripts/apps/admin.js"],
        chart: ["polyfills", "onload", "./galaxy/scripts/apps/chart.js"],
        extended: ["polyfills", "onload", "./galaxy/scripts/apps/extended.js"]
    },
    output: {
        path: path.join(__dirname, "../", "static/scripts/bundled"),
        // path: path.resolve(__dirname, "dist"), // test location
        filename: "[name].bundled.js",
        chunkFilename: "[name].chunk.js"
    },
    resolve: {
        modules: [scriptsBase, "node_modules"],
        alias: {
            vue: "vue/dist/vue.js",
            jquery$: path.resolve(__dirname, "galaxy/scripts/jquery-custom.js"),
            jqueryVendor$: path.resolve(__dirname, "node_modules/jquery/dist/jquery.js")
        }
    },
    optimization: {
        splitChunks: {
            cacheGroups: {
                libs: {
                    name: "libs",
                    test: /(node_modules|galaxy\/scripts\/(libs|ui|utils)\/)/,
                    chunks: "initial"
                }
            }
        }
    },
    module: {
        rules: [
            // Manual shimming for standard, horrible, jquery plugins
            {
                test: /jquery\.(migrate|autocomplete|event\.hover|event\.drag|form|rating|dynatree)/,
                use: "imports-loader?jQuery=jqueryVendor"
            },
            {
                test: /(select2|jstorage|farbtastic)/,
                use: "imports-loader?jQuery=jqueryVendor"
            },
            {
                test: /jquery-ui\.js/,
                use: "imports-loader?jQuery=jqueryVendor"
            },
            // Even MORE special handling!
            {
                test: /jquery\.mousewheel/,
                use: "imports-loader?define=>false,jQuery=jqueryVendor"
            },
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
                test: require.resolve("underscore"),
                use: [
                    {
                        loader: "expose-loader",
                        options: "_"
                    },
                    {
                        loader: "expose-loader",
                        options: "underscore"
                    }
                ]
            },
            {
                test: /\.css$/,
                use: ["style-loader", "css-loader"]
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
            _: "underscore",
            Backbone: "backbone"
        }),
        new VueLoaderPlugin()
    ]
};

if (process.env.GXY_BUILD_SOURCEMAPS || process.env.NODE_ENV == "development") {
    buildconfig.devtool = "source-map";
}

module.exports = buildconfig;
