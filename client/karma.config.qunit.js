const baseKarmaConfig = require("./karma.config.base");

// NOTE: tests currently fail in single pack mode because of select2,
// need to fix jquery bundle, so we never run them that way until
// they can be fixed.
// (process.env.GALAXY_TEST_AS_SINGLE_PACK || false);
const single_pack_mode = true;

const QUNIT_TESTS_SEPARATE_PACKS = [
    "galaxy/scripts/qunit/tests/galaxy_app_base_tests.js",
    // Something is funky with form_tests.js - needs to come before all other tests.
    "galaxy/scripts/qunit/tests/form_tests.js",
    "galaxy/scripts/qunit/tests/upload_dialog_tests.js",
    // Something is funky with masthead_tests - needs to come before one of the other
    // tests - not sure which though...
    "galaxy/scripts/qunit/tests/masthead_tests.js",
    //{pattern: 'galaxy/scripts/qunit/tests/list_of_pairs_collection_creator_tests.js', watched: false},
    "galaxy/scripts/qunit/tests/graph_tests.js",
    "galaxy/scripts/qunit/tests/hda_base_tests.js",
    "galaxy/scripts/qunit/tests/history_contents_model_tests.js",
    "galaxy/scripts/qunit/tests/job_dag_tests.js",
    "galaxy/scripts/qunit/tests/metrics_logger_tests.js",
    "galaxy/scripts/qunit/tests/popover_tests.js",
    "galaxy/scripts/qunit/tests/utils_tests.js",
    // "galaxy/scripts/qunit/tests/page_tests.js",
    "galaxy/scripts/qunit/tests/workflow_editor_tests.js",
    "galaxy/scripts/qunit/tests/modal_tests.js"
    // The following tests don't work for state reasons:

    // Error: Following test works on its own or with rest but not with
    //     list_of_pairs_collection_creator in the same suite. Not as much isolation
    //     as seperate page setup of previous runner.
    // {pattern: 'galaxy/scripts/qunit/tests/ui_tests.js', watched: false},
];

// these will not run individually because of $.fn.select2 error
// The comments in the above script block kind of reference that.
// Fix is most likely the jquery custom bundle implementation.
// const QUNIT_TESTS_SEPARATE_PACKS = [
//     "galaxy/**/qunit/**/*_tests.js"
// ]

const QUNIT_TESTS_AS_SINGLE_PACK = [
    "galaxy/**/qunit/test.js"
];


// Non-test assets that will be served by web server. 
// CSS needed by tests.
// Yeah... I dispute the validity of unit tests that requre 
// css to function. That sounds like something that would more
// appropriately be tested by selenium, if at all.

const assets = [
    "galaxy/scripts/qunit/assets/*.css"
];


module.exports = function (config) {

    let testFiles = single_pack_mode
        ? QUNIT_TESTS_AS_SINGLE_PACK
        : QUNIT_TESTS_SEPARATE_PACKS;

    let preprocessors = testFiles.reduce((result, file) => {
        result[file] = ["webpack"];
        return result;
    }, {});

    let settings = Object.assign({}, baseKarmaConfig, {
        frameworks: ["qunit"],
        files: testFiles.concat(assets),
        preprocessors: preprocessors
    });

    config.set(settings);
};
