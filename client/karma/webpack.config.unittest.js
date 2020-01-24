/**
 * Unit tests should not require css or images, so replace all those things with
 * the ignore-loader for speedier testing.
 */

const merge = require("webpack-merge");
const baseConfig = require("../webpack.config");

module.exports = (env, argv) => {

    const wpConfig = baseConfig(env, argv);
    wpConfig.mode = "development";
    wpConfig.entry = () => ({});

    // Don't need any assets for unit testing
    let ignoreAssetLoaders = {
        rules:[
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
    };

    wpConfig.module = merge.smart(wpConfig.module, ignoreAssetLoaders);


    // Using babel-plugin-rewire to handle dependency mocking since webpack 4
    // exports immutable bindings for ES modules but we still need a way to
    // overwrite dependencies during unit-testing.

    wpConfig.module.rules = wpConfig.module.rules.map(rule => {
        if (rule.loader == "babel-loader") {
            rule.options.plugins.push("rewire");
        }
        return rule;
    });

    return wpConfig;
}
