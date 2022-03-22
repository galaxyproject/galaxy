/**
 * Qunit Tests
 *
 * These legacy QUnit tests are interdependent and only execute as a single
 * package. A flaw in the previous node environment parameter-checking in the
 * old karma configs gave the illusion that they ran individually, but they do
 * not and probably never have. Keeping them around for now, but we should get
 * rid of them by rewriting the tests or preferrably by removing the code to
 * which they apply.
 */

const baseKarmaConfig = require("./karma.config.base");
const testFiles = ["polyfills.js", "../tests/qunit/testBundle.js"];
const preprocessors = testFiles.reduce((result, path) => {
    result[path] = ["webpack"];
    return result;
}, {});

module.exports = function (config) {
    const baseConfig = baseKarmaConfig(config);

    const settings = Object.assign({}, baseConfig, {
        files: testFiles,
        preprocessors: preprocessors,
        frameworks: ["polyfill", "qunit"],
        singleRun: true,
    });

    config.set(settings);
};
