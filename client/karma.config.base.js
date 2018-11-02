var webpackConfig = require("./webpack.config.unittest");

module.exports = {
    basepath: ".",
    failOnEmptyTestSuite: false,
    webpack: webpackConfig,
    webpackMiddleware: { noInfo: true },
    browsers: ["ChromeHeadlessNoSandbox"],
    singleRun: true,
    client: {
        captureConsole: true
    },
    customLaunchers: {
        ChromeHeadlessNoSandbox: {
            base: "ChromeHeadless",
            flags: ["--no-sandbox"]
        }
    }
}
