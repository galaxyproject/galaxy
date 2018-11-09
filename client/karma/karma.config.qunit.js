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
const webpackConfig = require("./webpack.config.unittest");

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
        frameworks: ["polyfill", "qunit"],
        webpack: webpackConfig
    });

    config.set(settings);
};


/*
var QUNIT_TESTS_SEPARATE_PACKS = [
    { pattern: "galaxy/scripts/qunit/tests/galaxy_app_base_tests.js", watched: false },
    // Something is funky with form_tests.js - needs to come before all other tests.
    { pattern: "galaxy/scripts/qunit/tests/form_tests.js", watched: false },
    { pattern: "galaxy/scripts/qunit/tests/upload_dialog_tests.js", watched: false },
    // Something is funky with masthead_tests - needs to come before one of the other
    // tests - not sure which though...
    { pattern: "galaxy/scripts/qunit/tests/masthead_tests.js", watched: false },
    //{pattern: 'galaxy/scripts/qunit/tests/list_of_pairs_collection_creator_tests.js', watched: false},
    { pattern: "galaxy/scripts/qunit/tests/graph_tests.js", watched: false },
    { pattern: "galaxy/scripts/qunit/tests/hda_base_tests.js", watched: false },
    { pattern: "galaxy/scripts/qunit/tests/history_contents_model_tests.js", watched: false },
    { pattern: "galaxy/scripts/qunit/tests/job_dag_tests.js", watched: false },
    { pattern: "galaxy/scripts/qunit/tests/metrics_logger_tests.js", watched: false },
    { pattern: "galaxy/scripts/qunit/tests/popover_tests.js", watched: false },
    { pattern: "galaxy/scripts/qunit/tests/utils_tests.js", watched: false },
    { pattern: "galaxy/scripts/qunit/tests/page_tests.js", watched: false },
    { pattern: "galaxy/scripts/qunit/tests/workflow_editor_tests.js", watched: false },
    { pattern: "galaxy/scripts/qunit/tests/modal_tests.js", watched: false }
    // The following tests don't work for state reasons:

    // Error: Following test works on its own or with rest but not with
    //     list_of_pairs_collection_creator in the same suite. Not as much isolation
    //     as seperate page setup of previous runner.
    // {pattern: 'galaxy/scripts/qunit/tests/ui_tests.js', watched: false},
];
*/