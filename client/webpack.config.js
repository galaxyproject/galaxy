/* eslint-env node */
const webpack = require("webpack");
const path = require("path");
const VueLoaderPlugin = require("vue-loader/lib/plugin");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const CssMinimizerPlugin = require("css-minimizer-webpack-plugin");
const DuplicatePackageCheckerPlugin = require("@cerner/duplicate-package-checker-webpack-plugin");
const { DumpMetaPlugin } = require("dumpmeta-webpack-plugin");
const TsconfigPathsPlugin = require("tsconfig-paths-webpack-plugin");
const TerserPlugin = require("terser-webpack-plugin");

const scriptsBase = path.join(__dirname, "src");
const testsBase = path.join(__dirname, "tests");
const libsBase = path.join(scriptsBase, "libs");
const styleBase = path.join(scriptsBase, "style");

const modulesExcludedFromLibs = [
    "jspdf",
    "canvg",
    "prismjs",
    "html2canvas",
    "handsontable",
    "pikaday",
    "moment",
    "elkjs",
    "@citation-js",
    "citeproc",
    "vega",
    "vega-embed",
    "vega-lite",
    "ace-builds",
].join("|");

const buildDate = new Date();

module.exports = (env = {}, argv = {}) => {
    // environment name based on -d, -p, webpack flag
    const targetEnv = process.env.NODE_ENV == "production" || argv.mode == "production" ? "production" : "development";

    let minimizations = {};
    if (targetEnv == "production") {
        minimizations = {
            minimize: true,
            minimizer: [new TerserPlugin(), new CssMinimizerPlugin()],
        };
    } else {
        minimizations = {
            minimize: false,
        };
    }

    const buildconfig = {
        mode: targetEnv,
        entry: {
            analysis: ["polyfills", "bundleEntries", "entry/analysis"],
            generic: ["polyfills", "bundleEntries", "entry/generic"],
        },
        output: {
            path: path.join(__dirname, "dist"),
            filename: "[name].bundled.js",
            clean: true,
        },
        resolve: {
            plugins: [new TsconfigPathsPlugin({ extensions: [".ts", ".js", ".json", ".vue", ".scss"] })],
            extensions: [".ts", ".js", ".json", ".vue", ".scss"],
            modules: [scriptsBase, "node_modules", styleBase, testsBase],
            fallback: {
                timers: require.resolve("timers-browserify"),
                stream: require.resolve("stream-browserify"),
                "process/browser": require.resolve("process/browser"),
                querystring: require.resolve("querystring-es3"),
                util: require.resolve("util/"),
                assert: require.resolve("assert/"),
            },
            alias: {
                vue$: path.resolve(__dirname, "node_modules/vue/dist/vue.esm.js"),
                jquery$: `${libsBase}/jquery.custom.js`,
                jqueryVendor$: `${libsBase}/jquery/jquery.js`,
                storemodern$: "store/dist/store.modern.js",
                "popper.js": path.resolve(__dirname, "node_modules/popper.js/"),
                underscore: path.resolve(__dirname, "node_modules/underscore"),
                // client-side application config
                config$: path.join(scriptsBase, "config", targetEnv) + ".js",
            },
        },
        optimization: {
            splitChunks: {
                cacheGroups: {
                    styles: {
                        name: "base",
                        chunks: "all",
                        test: (m) => m.constructor.name == "CssModule",
                        priority: -5,
                    },
                    libs: {
                        name: "libs",
                        test: new RegExp(`node_modules[\\/](?!(${modulesExcludedFromLibs})[\\/])|galaxy/scripts/libs`),
                        chunks: "all",
                        priority: -10,
                    },
                },
            },
            ...minimizations,
        },
        module: {
            rules: [
                {
                    test: /\.vue$/,
                    loader: "vue-loader",
                },
                {
                    test: /\.tsx?$/,
                    exclude: /node_modules/,
                    use: [
                        {
                            loader: "thread-loader",
                            options: { workers: 2 },
                        },
                        {
                            loader: "ts-loader",
                            options: {
                                transpileOnly: true,
                                configFile: "tsconfig.webpack.json",
                                appendTsSuffixTo: [/\.vue$/],
                            },
                        },
                    ],
                },
                {
                    test: /\.mjs$/,
                    include: /node_modules/,
                    type: "javascript/auto",
                },
                {
                    test: `${libsBase}/jquery.custom.js`,
                    loader: "expose-loader",
                    options: {
                        exposes: ["$", "jQuery"],
                    },
                },
                {
                    test: require.resolve("underscore"),
                    use: [
                        {
                            loader: "expose-loader",
                            options: {
                                exposes: {
                                    globalName: ["underscore", "_"],
                                },
                            },
                        },
                    ],
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
                            options: {
                                exposes: "bundleEntries",
                            },
                        },
                    ],
                },
                {
                    test: `${scriptsBase}/onload/loadConfig.js`,
                    use: [
                        {
                            loader: "expose-loader",
                            options: { exposes: "config" },
                        },
                    ],
                },
                {
                    test: /\.(sa|sc|c)ss$/,
                    use: [
                        {
                            loader: MiniCssExtractPlugin.loader,
                            options: {},
                        },
                        {
                            loader: "css-loader",
                            options: { sourceMap: true },
                        },
                        {
                            loader: "postcss-loader",
                        },
                        {
                            loader: "sass-loader",
                            options: {
                                sourceMap: true,
                                sassOptions: {
                                    quietDeps: true,
                                    includePaths: [
                                        path.join(styleBase, "scss"),
                                        path.resolve(__dirname, "./node_modules"),
                                    ],
                                },
                            },
                        },
                    ],
                },
                {
                    test: /\.(txt|tmpl)$/,
                    loader: "raw-loader",
                },
                {
                    test: /\.ya?ml$/,
                    use: "yaml-loader",
                },
            ],
        },
        resolveLoader: {
            alias: {
                // since we support both requirejs i18n and non-requirejs and both use a similar syntax,
                // use an alias so we can just use one file
                i18n: "amdi18n-loader",
            },
        },
        plugins: [
            // this plugin allows using the following keys/globals in scripts (w/o req'ing them first)
            // and webpack will automagically require them in the bundle for you
            new webpack.ProvidePlugin({
                $: `${libsBase}/jquery.custom.js`,
                jQuery: `${libsBase}/jquery.custom.js`,
                "window.jQuery": `${libsBase}/jquery.custom.js`,
                _: "underscore",
                Backbone: "backbone",
                Galaxy: ["app", "monitor"],
                Buffer: ["buffer", "Buffer"],
                process: "process/browser",
            }),
            new webpack.DefinePlugin({
                __targetEnv__: JSON.stringify(targetEnv),
                __buildTimestamp__: JSON.stringify(buildDate.toISOString()),
                __license__: JSON.stringify(require("./package.json").license),
            }),
            new VueLoaderPlugin(),
            new MiniCssExtractPlugin({
                filename: "[name].css",
            }),
            new DuplicatePackageCheckerPlugin(),
            new DumpMetaPlugin({
                filename: path.join(__dirname, "../lib/galaxy/web/framework/meta.json"),
                prepare: (stats) => ({
                    // add any other information you need to dump
                    hash: stats.hash,
                    epoch: Date.parse(buildDate),
                }),
            }),
        ],
        cache: {
            type: "filesystem",
            buildDependencies: {
                config: [__filename],
            },
        },
        devServer: {
            client: {
                overlay: {
                    errors: true,
                    warnings: false,
                },
                webSocketURL: {
                    port: process.env.GITPOD_WORKSPACE_ID ? 443 : undefined,
                },
            },
            allowedHosts: process.env.GITPOD_WORKSPACE_ID ? "all" : "auto",
            devMiddleware: {
                publicPath: "/static/dist",
                writeToDisk: true,
            },
            hot: true,
            port: process.env.WEBPACK_PORT || 8081,
            host: "0.0.0.0",
            // proxy *everything* to the galaxy server.
            // someday, when we have a fully API-driven independent client, this
            // can be a more limited set -- e.g. `/api`, `/auth`
            proxy: {
                "**": {
                    // We explicitly use ipv4 loopback instead of localhost to
                    // avoid ipv6/ipv4 resolution order issues; this should
                    // align with Galaxy's default.
                    target: process.env.GALAXY_URL || "http://127.0.0.1:8080",
                    secure: process.env.CHANGE_ORIGIN ? !process.env.CHANGE_ORIGIN : true,
                    changeOrigin: !!process.env.CHANGE_ORIGIN,
                    logLevel: "debug",
                },
            },
        },
    };

    if (process.env.GXY_BUILD_SOURCEMAPS) {
        buildconfig.devtool = "eval-cheap-module-source-map";
    }

    return buildconfig;
};
