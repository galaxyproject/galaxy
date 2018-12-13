/* eslint-env node */
const webpack = require("webpack");
const path = require("path");
const VueLoaderPlugin = require("vue-loader/lib/plugin");
const OptimizeCssAssetsPlugin = require("optimize-css-assets-webpack-plugin");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const DuplicatePackageCheckerPlugin = require("duplicate-package-checker-webpack-plugin");

const scriptsBase = path.join(__dirname, "galaxy/scripts");
const libsBase = path.join(scriptsBase, "libs");
const styleBase = path.join(__dirname, "galaxy/style");
const imageBase = path.join(__dirname, "../static/style");

let buildconfig = {
    entry: {
        login: ["onload", "apps/login"],
        analysis: ["onload", "apps/analysis"],
        admin: ["onload", "apps/admin"],
        extended: ["onload", "apps/extended"]
    },
    output: {
        path: path.join(__dirname, "../", "static/scripts/bundled"),
        filename: "[name].bundled.js",
        chunkFilename: "[name].chunk.js"
    },
    resolve: {
        modules: [scriptsBase, "node_modules", styleBase, imageBase],
        alias: {
            jquery$: `${libsBase}/jquery.custom.js`,
            jqueryVendor$: `${libsBase}/jquery/jquery.js`,
            store$: "store/dist/store.modern.js"
        }
    },
    optimization: {
        splitChunks: {
            cacheGroups: {
                styles: {
                    name: "base",
                    chunks: "all",
                    test: m => m.constructor.name == "CssModule",
                    priority: -5
                },
                libs: {
                    name: "libs",
                    test: /(node_modules|galaxy\/scripts\/(?!apps)).*\.(vue|js)$/, // .*\.(vue|js)$
                    chunks: "all",
                    priority: -10
                }
            }
        }
    },
    module: {
        rules: [
            {
                test: /\.vue$/,
                loader: "vue-loader"
            },
            {
                test: /\.js$/,
                // Pretty sure we don't want anything except node_modules here
                exclude: [
                    /(node_modules\/(?!(handsontable)\/)|bower_components)/,
                    libsBase
                ],
                loader: "babel-loader",
                options: { babelrc: true }
            },
            {
                test: `${libsBase}/jquery.custom.js`,
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
                test: /\.(png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot)(\?.*$|$)/,
                use: {
                    loader: "file-loader",
                    options: {
                        outputPath: "assets",
                        publicPath: "/static/scripts/bundled/assets/"
                    }
                }
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
                use: [
                    MiniCssExtractPlugin.loader,
                    {
                        loader: "css-loader",
                        options: { sourceMap: true }
                    }
                ]
            },
            {
                test: /\.scss$/,
                use: [
                    MiniCssExtractPlugin.loader,
                    {
                        loader: "css-loader",
                        options: { sourceMap: true }
                    },
                    {
                        loader: "sass-loader",
                        options: { sourceMap: true }
                    }
                ]
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
            $: `${libsBase}/jquery.custom.js`,
            jQuery: `${libsBase}/jquery.custom.js`,
            _: "underscore",
            Backbone: "backbone",
            Galaxy: ["app", "monitor"]
        }),
        new VueLoaderPlugin(),
        new MiniCssExtractPlugin({
            filename: "[name].css",
            sourceMap: true
        }),
        // https://github.com/webpack-contrib/mini-css-extract-plugin/issues/141
        new OptimizeCssAssetsPlugin({
            cssProcessorOptions: {
                map: {
                    inline: false,
                    annotation: true
                }
            }
        }),
        new DuplicatePackageCheckerPlugin()
    ]
};

if (process.env.GXY_BUILD_SOURCEMAPS || process.env.NODE_ENV == "development") {
    buildconfig.devtool = "source-map";
}

module.exports = buildconfig;

