const path = require('path');
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const CopyPlugin = require('copy-webpack-plugin');


module.exports = {
    mode: "production",
    entry: "./src/index.js",
    output: {
        filename: "script.js",
        path: path.resolve(__dirname, "static/js")
    },
    'target': 'web',
    plugins: [
        new MiniCssExtractPlugin(),
        new CopyPlugin({
            patterns: [
            {from: 'src/css/images', to: 'images'},
            {from: 'src/images/lorikeet', to: 'images'},
            ]
        }),
    ],
    module: {
        rules: [
            {
                test: /\.(png|svg|jpg|gif)$/,
                use: ['file-loader'],
            },
            {
                test: /\.css$/i,
                use: ['style-loader', 'css-loader'],
            },
            {
                test: /\.(woff|woff2)(\?v=\d+\.\d+\.\d+)?$/,
                loader: 'file-loader',
                options: {
                    outputPath: "static/js",
                },
            },
            {
                test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/,
                use: ['file-loader'],
            },
            {test: /\.eot(\?v=\d+\.\d+\.\d+)?$/, loaders: "file-loader"},
        ],
    },
    performance: {
        hints: false
    }
};