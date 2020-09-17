const webpack = require("webpack");
const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const CopyPlugin = require('copy-webpack-plugin');

module.exports = {
    mode: 'production',
    entry: "./src/index.js",
    output: {
        filename: "script.js",
        path: path.resolve(__dirname, "static/dist")
    },
    plugins: [
        new MiniCssExtractPlugin(),
        new webpack.ProvidePlugin({
            underscore: 'underscore',
            _: 'underscore'

        }),
        new CopyPlugin([
            {from: 'src/images', to: 'images'},
        ]),
    ],
    module: {
        rules: [
            {
                test: /\.css$/i,
                use: [MiniCssExtractPlugin.loader, 'css-loader'],
            },
            {
                test: /\.(woff|woff2)(\?v=\d+\.\d+\.\d+)?$/,
                loader: "url-loader",
                options: {limit: 10000, mimetype: "application/font-woff"}
            },
            {
                test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/,
                loader: "url-loader",
                options: {limit: 10000, mimetype: "application/octet-stream"}
            },
            {test: /\.eot(\?v=\d+\.\d+\.\d+)?$/, loaders: "file-loader"},
            {
                test: /\.svg(\?v=\d+\.\d+\.\d+)?$/,
                loaders: "url-loader",
                options: {limit: 10000, mimetype: "image/svg+xml"}
            }
        ]
    },
    target: 'web'
};