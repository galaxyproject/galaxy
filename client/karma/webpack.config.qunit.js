/**
 * So the legacy QUnit tests have to perform some gymastics that should not be
 * required because thse tests apparently care about assets like the CSS and images.
 * TODO: Replace these tests with like... actual unit tests.
 */

let wpConfig = require("../webpack.config");
wpConfig.mode = "production";
wpConfig.entry = () => ({});

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
const scrubLoaderRules = (module) => {
    let rePluginMatch = /mini-css-extract-plugin/;
    let styleLoader = { loader: "style-loader" };
    let processor = switchPlugin(rePluginMatch, styleLoader);
    module.rules = module.rules.map(processor);
}

// Remove mini-css-extract loader references
scrubLoaderRules(wpConfig.module);

// remove MiniCSSExtract Plugin
wpConfig.plugins = wpConfig.plugins.filter(p => {
    return p.constructor.name != "MiniCssExtractPlugin";
});

module.exports = wpConfig;
