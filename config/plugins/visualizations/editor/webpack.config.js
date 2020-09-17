const webpack = require("webpack");
const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

module.exports = {
    mode: 'production',
    entry: path.resolve(__dirname, "src/index.js"),
    output: {
        filename: "script.js",
        path: path.resolve(__dirname, "static")
    },
    plugins: [
        new MiniCssExtractPlugin(),
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
};
