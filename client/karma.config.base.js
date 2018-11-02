var webpackConfig = require("./webpack.config.test");

module.exports = {
    basepath: ".",
    failOnEmptyTestSuite: false,
    webpack: webpackConfig,
    webpackMiddleware: { noInfo: false },
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
