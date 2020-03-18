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

module.exports = (env = {}, argv = {}) => {
    // environment name based on -d, -p, webpack flag
    const targetEnv = argv.mode || "development";

    const buildconfig = {
        entry: {
            login: ["polyfills", "bundleEntries", "entry/login"],
            analysis: ["polyfills", "bundleEntries", "entry/analysis"],
            admin: ["polyfills", "bundleEntries", "entry/admin"],
            generic: ["polyfills", "bundleEntries", "entry/generic"]
        },
        output: {
            path: path.join(__dirname, "../", "/static/dist"),
            publicPath: "/static/dist/",
            filename: "[name].bundled.js",
            chunkFilename: "[name].chunk.js"
        },
        resolve: {
            extensions: ["*", ".js", ".json", ".vue", ".scss"],
            modules: [scriptsBase, "node_modules", styleBase, imageBase],
            alias: {
                jquery$: `${libsBase}/jquery.custom.js`,
                jqueryVendor$: `${libsBase}/jquery/jquery.js`,
                storemodern$: "store/dist/store.modern.js",
                "popper.js": path.resolve(__dirname, "node_modules/popper.js/"),
                moment: path.resolve(__dirname, "node_modules/moment"),
                underscore: path.resolve(__dirname, "node_modules/underscore"),
                // client-side application config
                config$: path.join(__dirname, "galaxy", "config", targetEnv) + ".js"
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
                        test: /node_modules[\\/](?!(handsontable|pikaday|moment)[\\/])|galaxy\/scripts\/libs/,
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
                    /*
                     * Babel transpile excludes for:
                     * - all node_modules except for handsontable, bootstrap-vue
                     * - statically included libs (like old jquery plugins, etc.)
                    */
                    exclude: [/(node_modules\/(?!(handsontable|bootstrap-vue)\/))/, libsBase],
                    loader: "babel-loader",
                    options: {
                        cacheDirectory: true,
                        cacheCompression: false,
                        presets: [["@babel/preset-env", { modules: false }]],
                        plugins: ["transform-vue-template", "@babel/plugin-syntax-dynamic-import"],
                        ignore: ["i18n.js", "utils/localization.js", "nls/*"]
                    }
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
                            publicPath: "../dist/assets/"
                        }
                    }
                },
                // Alternative to setting window.bundleEntries
                // Just import "bundleEntries" in any endpoint that needs
                // access to these globals, or even-better, make
                // more endpoints and skip the global altogether
                {
                    test: `${scriptsBase}/bundleEntries`,
                    use: [
                        {
                            loader: "expose-loader",
                            options: "bundleEntries"
                        }
                    ]
                },
                {
                    test: `${scriptsBase}/onload/loadConfig.js`,
                    use: [
                        {
                            loader: "expose-loader",
                            options: "config"
                        }
                    ]
                },
                {
                    test: /\.(sa|sc|c)ss$/,
                    use: [
                        {
                            loader: MiniCssExtractPlugin.loader,
                            options: {
                                hmr: process.env.NODE_ENV === "development"
                            }
                        },
                        {
                            loader: "css-loader",
                            options: { sourceMap: true }
                        },
                        {
                            loader: "postcss-loader",
                            options: {
                                plugins: function() {
                                    return [require("autoprefixer")];
                                }
                            }
                        },
                        {
                            loader: "sass-loader",
                            options: {
                                sourceMap: true,
                                sassOptions: {
                                    includePaths: ["galaxy/style/scss", path.resolve(__dirname, "./node_modules")]
                                }
                            }
                        }
                    ]
                },
                {
                    test: /\.(txt|tmpl)$/,
                    loader: "raw-loader"
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
        ],
        devServer: {
            hot: true
        }
    };

    if (process.env.GXY_BUILD_SOURCEMAPS || process.env.NODE_ENV == "development") {
        buildconfig.devtool = "source-map";
    }

    return buildconfig;
};
