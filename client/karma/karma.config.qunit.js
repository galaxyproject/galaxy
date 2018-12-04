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

const testFiles = [
    "qunit/test.js"
];

const assets = [
    "qunit/assets/*.css"
];

module.exports = function (config) {

    let preprocessors = testFiles.reduce((result, path) => {
        result[path] = ["webpack"];
        return result;
    }, {});

    let settings = Object.assign({}, baseKarmaConfig, {
        files: testFiles.concat(assets),
        preprocessors: preprocessors,
        frameworks: ["polyfill", "qunit"]
    });

    config.set(settings);
};
