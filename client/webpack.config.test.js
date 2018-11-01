/**
 * Take the fun parts out of the webpack config so the unit-tests run
 */

let wpConfig = require("./webpack.config");


const switchPlugin = (reMatcher, replacement) => {

    let scrubLoader = (obj) =>
        (typeof obj == "string" && obj.match(reMatcher))
            ? Object.assign({}, replacement)
            : obj

    return (rule) => {
        if (rule.use && rule.use.length) {
            rule.use = rule.use.map(scrubLoader);
        }
        return rule;
    }
}


// set mode?
wpConfig.mode = "development";

// Don't build Galaxy bundles - build per-test bundles.
wpConfig.entry = () => ({});

// Remove MiniCssExtractPlugin loader references
// replace mini-css-extract plugin with basic style loader
// Honestly I'm not clear on why we process css at all for unit tests
let rePluginMatch = /mini-css-extract-plugin/;
let styleLoader = { loader: "style-loader" };
let processor = switchPlugin(rePluginMatch, styleLoader);
wpConfig.module.rules = wpConfig.module.rules.map(processor);


module.exports = wpConfig;