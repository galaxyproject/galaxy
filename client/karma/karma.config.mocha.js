/**
 * Runs mocha tests
 *
 * Individual files can be run by passing in a comma-delimited list
 * of globs for the karma config like this:
 *
 *    npm run test-watch watch-only="Tags.test.js,something.js,doodads.js"
 */

const baseKarmaConfig = require("./karma.config.base");

// Complete list of unit tests
const defaultFiles = [
    // component/module tests
    "**/*.test.js",
    // pre-existing rules definition tests
    "**/mocha/tests/*_tests.js"
];

function getTestFiles() {
    // check for user-supplied list
    let userPatterns = getUserTestGlobs();
    let patterns = userPatterns.length ? userPatterns : defaultFiles;
    return patterns.map(pattern => ({ pattern, watched: true}));
}

// command line arg "watch-only" can be a list of file globs
// for karma to watch
function getUserTestGlobs() {
    let userGlobs = process.argv.find(s => s.startsWith("watch-only"));
    return userGlobs ? processUserGlobs(userGlobs) : [];
}

// split command line arg into an array
function processUserGlobs(val) {
    let result = [];
    let fileListString = val.split("=")[1];
    if (fileListString) {
        result = fileListString.split(",")
            .map(s => s.trim())
            .map(checkGlobPrefix);
    }
    return result;
}

// prefixes user-supplied glob with directory wildcard
function checkGlobPrefix(glob) {
    return glob.startsWith("**/") ? glob : `**/${glob}`;
}

module.exports = function (config) {

    const baseConfig = baseKarmaConfig(config);

    let files = [
        "../../node_modules/@babel/polyfill/dist/polyfill.js",
        ...getTestFiles()
    ];

    let settings = Object.assign({}, baseConfig, {
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
