const webpack = require("webpack"),
    path = require("path"),
    MiniCssExtractPlugin = require("mini-css-extract-plugin");

module.exports = {
    entry: path.resolve(__dirname, "src/index.js"),
    output: {
        filename: "bundle.js",
        path: path.resolve(__dirname, "static")
    },
    plugins: [
        new MiniCssExtractPlugin()
    ],
    module: {
        rules: [
            {
                test: /\.css/,
                use: [MiniCssExtractPlugin.loader, "css-loader"]
            },
            {
                test: /\.(woff|woff2)(\?v=\d+\.\d+\.\d+)?$/,
                loader: "url-loader",
                options: { limit: 10000, mimetype: "application/font-woff" }
            },
            {
                test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/,
                loader: "url-loader",
                options: { limit: 10000, mimetype: "application/octet-stream" }
            },
            { test: /\.eot(\?v=\d+\.\d+\.\d+)?$/, loaders: "file-loader" },
            {
                test: /\.svg(\?v=\d+\.\d+\.\d+)?$/,
                loaders: "url-loader",
                options: { limit: 10000, mimetype: "image/svg+xml" }
            }
        ]
    },
    resolve: {
        modules: ["node_modules"],
        alias: {
            "phylotree.css": __dirname + "/node_modules/phylotree/build/phylotree.css",
            "hyphy-vision.css": __dirname + "/node_modules/hyphy-vision/dist/hyphyvision.css"
        }
    }
};
