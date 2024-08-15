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
        new webpack.ProvidePlugin({
            $: "jquery",
            jQuery: "jquery",
            d3: "d3",
            _: "underscore"
        })
    ],
    module: {
        rules: [
            {
                test: /\.css/,
                use: [MiniCssExtractPlugin.loader, "css-loader"]
            },
        ]
    },
    resolve: {
        modules: ["node_modules"],
        alias: {
            "phylotree.css": __dirname + "/node_modules/phylotree/phylotree.css",
            "hyphy-vision.css": __dirname + "/node_modules/hyphy-vision/dist/hyphyvision.css"
        }
    }
};
