/**
 * Runs mocha tests
 */

const baseKarmaConfig = require("./karma.config.base");

const single_pack = (process.env.GALAXY_TEST_AS_SINGLE_PACK == "true");

const testBundles = [
    "**/unitTestBundle.js",
    "**/mocha/test.js"
];

const separateTests = [
    "**/*.test.js",
    "**/mocha/tests/*_tests.js"
];

module.exports = function (config) {

    console.log("single_pack?", single_pack);

    // pick all separate tests or the dynamic test-bundles
    let files = single_pack
        ? testBundles
        : separateTests;

    let preprocessors = files.reduce((result, path) => {
        result[path] = ["webpack"];
        return result;
    }, {});

    let settings = Object.assign({}, baseKarmaConfig, {
        files: files,
        exclude: ["**/qunit/*"],
        preprocessors: preprocessors,
        reporters: ["mocha"],
        frameworks: ["polyfill", "mocha", "chai"]
    });

    config.set(settings);
}
