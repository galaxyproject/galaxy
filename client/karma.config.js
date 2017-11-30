
var webpackConfig = require('./webpack.config');

// CommonsChunkPlugin not compatible with karma.
// https://github.com/webpack-contrib/karma-webpack/issues/24
webpackConfig.plugins.splice(0, 1);

// Don't build Galaxy bundles - we build per-test bundles.
webpackConfig.entry = function() { return {}; };

// Single pack mode runs whole test suite much more quickly - but requires
// running the whole test suite so it would be slower for one-off tests.
var single_pack_mode = function(){
    return process.env.GALAXY_TEST_AS_SINGLE_PACK || false;
};

var TESTS_SEPARATE_PACKS = [
    {pattern: 'galaxy/scripts/qunit/tests/galaxy_app_base_tests.js', watched: false},
    // Something is funky with form_tests.js - needs to come before all other tests.
    {pattern: 'galaxy/scripts/qunit/tests/form_tests.js', watched: false},
    {pattern: 'galaxy/scripts/qunit/tests/upload_dialog_tests.js', watched: false},
    // Something is funky with masthead_tests - needs to come before one of the other
    // tests - not sure which though...
    {pattern: 'galaxy/scripts/qunit/tests/masthead_tests.js', watched: false},
    //{pattern: 'galaxy/scripts/qunit/tests/list_of_pairs_collection_creator_tests.js', watched: false},
    {pattern: 'galaxy/scripts/qunit/tests/graph_tests.js', watched: false},
    {pattern: 'galaxy/scripts/qunit/tests/hda_base_tests.js', watched: false},
    {pattern: 'galaxy/scripts/qunit/tests/history_contents_model_tests.js', watched: false},
    {pattern: 'galaxy/scripts/qunit/tests/job_dag_tests.js', watched: false},
    {pattern: 'galaxy/scripts/qunit/tests/metrics_logger_tests.js', watched: false},
    {pattern: 'galaxy/scripts/qunit/tests/popover_tests.js', watched: false},
    {pattern: 'galaxy/scripts/qunit/tests/utils_tests.js', watched: false},
    {pattern: 'galaxy/scripts/qunit/tests/page_tests.js', watched: false},
    {pattern: 'galaxy/scripts/qunit/tests/workflow_editor_tests.js', watched: false},
    {pattern: 'galaxy/scripts/qunit/tests/modal_tests.js', watched: false},
    // The following tests don't work for state reasons:

    // Error: Following test works on its own or with rest but not with 
    //     list_of_pairs_collection_creator in the same suite. Not as much isolation
    //     as seperate page setup of previous runner.
    // {pattern: 'galaxy/scripts/qunit/tests/ui_tests.js', watched: false},
];

var TESTS_AS_SINGLE_PACK = [
    {pattern: 'galaxy/scripts/qunit/test.js', watched: false},
];

// karma.conf.js
module.exports = function(config) {
  config.set({
    basepath: '.',
    files: (single_pack_mode() ? TESTS_AS_SINGLE_PACK : TESTS_SEPARATE_PACKS).concat([
      // Non-test assets that will be served by web server.
      // CSS needed by tests.
      'galaxy/scripts/qunit/assets/*.css',
    ]),
    plugins: [
      'karma-webpack',
      'karma-qunit',
      'karma-polyfill',
      'karma-phantomjs-launcher',
    ],
    polyfill: [ 'Object.assign' ],
    // browsers: [ 'PhantomJS' ],
    // logLevel: config.LOG_DEBUG,

    // Tried to do some awesome babel, ES6 stuff in here but I was encountering
    // problems so I simplified - might be worth adding it back in though now
    // that we have a working setup.
    preprocessors: {
      // add webpack as preprocessor
      'galaxy/scripts/qunit/**/*.js': ['webpack']
    },

    frameworks: ['polyfill', 'qunit'],

    webpack: webpackConfig,
    webpackMiddleware: { noInfo: false }
  });
};
