var path = require("path");
var croot = path.resolve(__dirname, "../../../../");
var webpack = require("webpack");
var lroot = path.resolve(croot, "client/galaxy/scripts/libs");

module.exports = {
    entry: path.resolve(__dirname, "./src/scatterplot.js"),
    output: {
        path: path.resolve(__dirname, "static"),
        filename: "scatterplot.bundle.js"
    },
    resolve: {
        modules: [path.resolve(croot, "client/galaxy/scripts"), path.resolve(croot, "client/node_modules")],
        alias: {
            jquery: path.join(lroot, "jquery/jquery"),
            underscore: path.join(lroot, "underscore.js"),
            backbone: path.join(lroot, "backbone.js"),
        }
    },
    resolveLoader: {
        alias: {
            // since we support both requirejs i18n and non-requirejs and both use a similar syntax,
            // use an alias so we can just use one file
            i18n: "amdi18n-loader"
        }
    },
    module: {
        rules: [
            {
                test: /\.js$/,
                exclude: [/(node_modules|bower_components)/, lroot],
                loader: "babel-loader"
            }
        ]
    },
    plugins: [
        new webpack.ProvidePlugin({
            jquery: "jquery",
            jQuery: "jquery",
            $: "jquery"
        })
    ]
};
