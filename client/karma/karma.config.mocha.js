/**
 * Runs mocha tests
 * 
 * Individual files can be run by passing in a comma-delimited list
 * of globs for the karma config like this:
 * 
 *    env KARMA_TESTS="Tags.test.js,something.js,doodads.js" npm run test-watch
 */

const baseKarmaConfig = require("./karma.config.base");


// Unless we have an environment variable picking out
// a specified set of files, this is what's going to run
const defaultFiles = [
    // component/module tests
    "**/*.test.js",
    // pre-existing rules definition tests
    "**/mocha/tests/*_tests.js"
]

// allows running just a set list of files
function getTestFiles(testFiles) {
    let patterns = testFiles ? testFiles.split(",").map(checkGlobPrefix) : defaultFiles;
    return patterns.map(pattern => ({ pattern, watched: true}));
}

// prefixes user-supplied glob with directory wildcard
function checkGlobPrefix(glob) {
    if (!glob.startsWith("**/")) {
        return `**/${glob}`;
    }
    return glob;
}

module.exports = function (config) {

    // assemble test files, can run individuals by specifying
    // globs on command line
    let files = [
        "../../node_modules/@babel/polyfill/dist/polyfill.js",
        ...getTestFiles(process.env.KARMA_TESTS)
    ];

    let settings = Object.assign({}, baseKarmaConfig, {
        files,
        preprocessors: {
            "**/*.js": ["webpack"]
        },
        exclude: ["**/qunit/*"],
        reporters: ["mocha"],
        frameworks: ["mocha", "chai"]
    });

    config.set(settings);
}
