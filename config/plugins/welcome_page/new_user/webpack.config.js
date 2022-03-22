
const webpack = require("webpack");
const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const CopyPlugin = require('copy-webpack-plugin');


module.exports = {
    mode: 'production',
    entry: path.resolve(__dirname, "src/index.js"),
    output: {
        filename: "topics.js",
        path: path.resolve(__dirname, "dist")
    },
    plugins: [
        new MiniCssExtractPlugin(),
        new webpack.ProvidePlugin({
            $: "jquery",
            jQuery: "jquery",
            d3: "d3",
            _: "underscore"
        }),
        new CopyPlugin({
            patterns: [
                {from: 'node_modules/@galaxyproject/new_user_welcome', to: 'static/topics'}
            ],
        }),
    ],
    resolve: {
        modules: ["node_modules"],
    }
};
