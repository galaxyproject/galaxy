/**
 * Runs mocha tests
 */

const baseKarmaConfig = require("./karma.config.base");

module.exports = function (config) {

    let settings = Object.assign({}, baseKarmaConfig, {
        files: [
            "../../node_modules/@babel/polyfill/dist/polyfill.js",
            { pattern: "**/*.test.js", watched: true },
            // { pattern: "**/mocha/tests/*_tests.js" }
        ],
        preprocessors: {
            "**/*.js": ["webpack"]
        },
        exclude: ["**/qunit/*"],
        reporters: ["mocha"],
        frameworks: ["mocha", "chai"]
    });

    config.set(settings);
}
