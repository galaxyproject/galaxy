
const webpack = require("webpack");
const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const CopyPlugin = require('copy-webpack-plugin');


module.exports = {
    mode: 'production',
    entry: path.resolve(__dirname, "src/index.js"),
    output: {
        filename: "topics.js",
        path: path.resolve(__dirname, "static")
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
                {from: 'node_modules/galaxy_new_user_welcome', to: 'topics'}
                // {from: 'src/topics', to: 'topics'},
            ],
        }),
    ],
    // module: {
    //     rules: [
    //         {
    //             test: /\.json$/i,
    //             // type: 'asset/resource',
    //             use: {
    //                 loader: "file-loader",
    //             },
    //         },
    //         {
    //             test: /\.(png|svg|jpg|jpeg|gif)$/i,
    //             // type: 'asset/resource',
    //             use: {
    //                 loader: "file-loader",
    //             },
    //         },
    //     ]
    // },
    resolve: {
        modules: ["node_modules"],
    }
};
