/**
 * Base karma config, assumes chrome headless and webpack
 */

const webpackConfig = require("./webpack.config.unittest");

module.exports = {
    basePath: "../galaxy/scripts",
    browsers: ["ChromeHeadlessNoSandbox"],
    client: {
        captureConsole: true
    },
    failOnEmptyTestSuite: false,
    singleRun: true,
    webpack: webpackConfig,
    webpackMiddleware: {
        noInfo: true
    },
    customLaunchers: {
        ChromeHeadlessNoSandbox: {
            base: "ChromeHeadless",
            flags: ["--no-sandbox"]
        }
    }
}
