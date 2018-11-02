/**
 * Runs mocha tests
 */
const baseKarmaConfig = require("./karma.config.base");

// Single pack mode runs whole test suite much more quickly - but requires
// running the whole test suite so it would be slower for one-off tests.
const single_pack = (process.env.GALAXY_TEST_AS_SINGLE_PACK || false);

const testBundles = [
    "galaxy/**/unitTestBundle.js",
    "galaxy/**/mocha/test.js"
];

const separateTests = [
    "galaxy/scripts/**/*.test.js",
    "galaxy/**/mocha/tests/*_tests.js"
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
        exclude: ["galaxy/**/qunit/*"],
        preprocessors: preprocessors,
        reporters: ["mocha"],
        frameworks: ["mocha", "chai"]
    });

    config.set(settings);
}
