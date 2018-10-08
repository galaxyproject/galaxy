/* eslint-env node */
const webpack = require("webpack");
const path = require("path");
const VueLoaderPlugin = require("vue-loader/lib/plugin");

const scriptsBase = path.join(__dirname, "galaxy/scripts");
const libsBase = path.join(scriptsBase, "libs");

let buildconfig = {
    entry: {
        login: ["onload", "./galaxy/scripts/apps/login.js"],
        analysis: ["onload", "./galaxy/scripts/apps/analysis.js"],
        admin: ["onload", "./galaxy/scripts/apps/admin.js"],
        extended: ["onload", "./galaxy/scripts/apps/extended.js"]
    },
    output: {
        path: path.join(__dirname, "../", "static/scripts/bundled"),
        // path: path.resolve(__dirname, "dist"), // test location
        filename: "[name].bundled.js",
        chunkFilename: "[name].chunk.js"
    },
    resolve: {
        modules: [scriptsBase, "node_modules"]
    },
    optimization: {
        splitChunks: {
            cacheGroups: {
                libs: {
                    name: "libs",
                    test: /(node_modules|galaxy\/scripts\/(?!apps))/,
                    chunks: "initial"
                }
            }
        }
    },
    module: {
        rules: [
            {
                test: /\.vue$/,
                loader: "vue-loader",
                options: {
                    loaders: {
                        js: [
                            {
                                loader: "babel-loader",
                                options: { babelrc: true }
                            }
                        ]
                    }
                }
            },
            {
                test: /\.js$/,
                exclude: [/(node_modules\/(?!(handsontable)\/)|bower_components)/, libsBase],
                loader: "babel-loader",
                options: { babelrc: true }
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
            // Alternative to setting window.bundleEntries
            // Just import "extended" in any endpoint that needs
            // access to these globals, or even-better, make
            // more endpoints and skip the global altogether
            {
                test: /apps\/extended/,
                use: [
                    {
                        loader: "expose-loader",
                        options: "bundleEntries"
                    }
                ]
            },
            {
                test: /\.css$/,
                use: ["style-loader", "css-loader"]
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
