var webpackConfig = require("./webpack.config");

// Don't build Galaxy bundles - we build per-test bundles.
webpackConfig.entry = function() {
    return {};
};
webpackConfig.module.rules = webpackConfig.module.rules.slice(0, 6).concat([
    {
        test: /\.css$/,
        use: [
            { loader: "style-loader" },
            {
                loader: "css-loader",
                options: { sourceMap: true }
            }
        ]
    },
    {
        test: /\.scss$/,
        use: [
            { loader: "style-loader" },
            {
                loader: "css-loader",
                options: { sourceMap: true }
            },
            {
                loader: "sass-loader",
                options: { sourceMap: true }
            }
        ]
    },
    // Alternative to setting window.bundleEntries
    // Just import "extended" in any endpoint that needs
    // access to these globals, or even-better, make
    // more endpoints and skip the global altogether
    {
        test: /apps\/extended/,
        use: [
            {
                loader: "expose-loader",
                options: "bundleEntries"
            }
        ]
    }
]);

// Single pack mode runs whole test suite much more quickly - but requires
// running the whole test suite so it would be slower for one-off tests.
var single_pack_mode = function() {
    return process.env.GALAXY_TEST_AS_SINGLE_PACK || false;
};

var test_framework = function() {
    return process.env.GALAXY_TEST_FRAMEWORK || "qunit";
};

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

const QUNIT_TESTS_AS_SINGLE_PACK = [{ pattern: "galaxy/scripts/qunit/test.js", watched: false }];
const QUNIT_TEST_FILES = single_pack_mode() ? QUNIT_TESTS_AS_SINGLE_PACK : QUNIT_TESTS_SEPARATE_PACKS;
const MOCHA_TEST_FILES = [{ pattern: "galaxy/scripts/mocha/test.js", watched: false }];
const TEST_FILES = test_framework() == "qunit" ? QUNIT_TEST_FILES : MOCHA_TEST_FILES;
const FRAMEWORK_PLUGIN = test_framework() == "qunit" ? "karma-qunit" : "karma-mocha";

// karma.conf.js
module.exports = function(config) {
    config.set({
        basepath: ".",
        failOnEmptyTestSuite: false,
        files: TEST_FILES.concat([
            // Non-test assets that will be served by web server.
            // CSS needed by tests.
            "galaxy/scripts/qunit/assets/*.css"
        ]),
        plugins: ["karma-webpack", FRAMEWORK_PLUGIN, "karma-mocha", "karma-polyfill", "karma-phantomjs-launcher"],
        polyfill: ["Object.assign"],
        // browsers: [ 'PhantomJS' ],
        // logLevel: config.LOG_DEBUG,

        // Tried to do some awesome babel, ES6 stuff in here but I was encountering
        // problems so I simplified - might be worth adding it back in though now
        // that we have a working setup.
        preprocessors: {
            // add webpack as preprocessor
            "galaxy/scripts/qunit/**/*.js": ["webpack"],
            "galaxy/scripts/mocha/**/*.js": ["webpack"]
        },

        frameworks: ["polyfill", test_framework()],

        webpack: webpackConfig,
        webpackMiddleware: { noInfo: false }
    });
};
