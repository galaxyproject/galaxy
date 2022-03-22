/**
 * Base karma config, assumes chrome headless and webpack
 */

const webpackConfigFunc = require("./webpack.config.unittest");

module.exports = (config) => {
    // Karma does not execute the webpack config function by default
    const webpackConfig = webpackConfigFunc(
        {},
        {
            mode: "testing",
        }
    );

    return {
        basePath: "../../src",
        browsers: ["ChromeHeadlessNoSandbox"],
        client: {
            captureConsole: true,
        },
        failOnEmptyTestSuite: false,
        singleRun: true,
        webpack: webpackConfig,
        webpackMiddleware: {
            noInfo: true,
        },
        customLaunchers: {
            ChromeHeadlessNoSandbox: {
                base: "ChromeHeadless",
                flags: ["--no-sandbox"],
            },
        },
    };
};
