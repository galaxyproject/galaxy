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

    // Set exclude for babel-loader to completely ignore *all* node-modules,
    // without our exceptions to support IE as in parent webpack config.

    wpConfig.module.rules = wpConfig.module.rules.map((rule) => {
        if (rule.loader == "babel-loader") {
            rule.exclude = [/(node_modules\/)/];
        }
        return rule;
    });

    return wpConfig;
};
