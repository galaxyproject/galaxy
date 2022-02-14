const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const CopyPlugin = require("copy-webpack-plugin");

module.exports = {
    mode: "production",
    entry: "./src/index.js",
    output: {
        filename: "script.js",
        path: path.join(__dirname, "static/dist"),
    },
    target: "web",
    plugins: [
        new MiniCssExtractPlugin(),
        new CopyPlugin({
            patterns: [
                { from: "src/css/images", to: "images" },
                { from: "src/images/lorikeet", to: "images" },
            ],
        }),
    ],
    module: {
        rules: [
            {
                test: /\.css$/i,
                use: ["style-loader", "css-loader"],
            },
            {
                test: /\.(png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot)(\?.*$|$)/,
                use: {
                    loader: "file-loader",
                },
            },
        ],
    },
    performance: {
        hints: false,
    },
};
