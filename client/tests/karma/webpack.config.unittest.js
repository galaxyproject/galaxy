/**
 * Unit tests should not require css or images, so replace all those things with
 * the ignore-loader for speedier testing.
 */

const merge = require("webpack-merge");
const baseConfig = require("../../webpack.config");

module.exports = (env, argv) => {
    const wpConfig = baseConfig(env, argv);
    wpConfig.mode = "development";
    wpConfig.entry = () => ({});

    // Don't need any assets for unit testing
    const ignoreAssetLoaders = {
        rules: [
            {
                test: /\.(png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot)(\?.*$|$)/,
                loader: "ignore-loader",
            },
            {
                test: /\.css$/,
                loader: "ignore-loader",
            },
            {
                test: /\.scss$/,
                loader: "ignore-loader",
            },
        ],
    };

    wpConfig.module = merge.merge(wpConfig.module, ignoreAssetLoaders);

    return wpConfig;
};
