/**
 * So the legacy QUnit tests have to perform some gymastics that should not be
 * required because unit tests do not need access to css or images.
 *
 * TODO: replace or re-implement these tests so that they are actual unit tests,
 * remove all style checks to selenium or another more appropriate venue.
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


// Remove MiniCssExtractPlugin loader references
// replace mini-css-extract plugin with basic style loader
// Honestly I'm not clear on why we process css at all for unit tests
let rePluginMatch = /mini-css-extract-plugin/;
let styleLoader = { loader: "style-loader" };
let processor = switchPlugin(rePluginMatch, styleLoader);
wpConfig.module.rules = wpConfig.module.rules.map(processor);

module.exports = wpConfig;