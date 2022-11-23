const webpack = require("webpack");
const path = require("path");
const CopyPlugin = require("copy-webpack-plugin");

module.exports = {
    mode: "production",
    entry: path.resolve(__dirname, "src/index.js"),
    output: {
        filename: "topics.js",
        path: path.resolve(__dirname, "dist"),
    },
    plugins: [
        new CopyPlugin({
            patterns: [{ from: "node_modules/@galaxyproject/new_user_welcome", to: "static/topics" }],
        }),
    ],
    resolve: {
        modules: ["node_modules"],
    },
};
