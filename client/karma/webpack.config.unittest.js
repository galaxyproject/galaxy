/**
 * Unit tests should not require css or images, so replace all those things with
 * the ignore-loader for speedier testing.
 */

let merge = require("webpack-merge");
let wpConfig = require("../webpack.config");

wpConfig.mode = "development";
wpConfig.entry = () => ({});

// Don't need assets for unit testing, override those rules
module.exports = merge.smart(wpConfig, {
    module: {
        rules: [
            {
                test: /\.(png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot)(\?.*$|$)/,
                loader: "ignore-loader"
            },
            {
                test: /\.css$/,
                loader: "ignore-loader"
            },
            {
                test: /\.scss$/,
                loader: "ignore-loader"
            }
        ]
    }
});
