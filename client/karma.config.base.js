var webpackConfig = require("./webpack.config.test");

module.exports = {
    basepath: ".",
    failOnEmptyTestSuite: false,
    webpack: webpackConfig,
    webpackMiddleware: { noInfo: false },
    browsers: ["ChromeHeadless"],
    client: {
        captureConsole: true
    }
}
