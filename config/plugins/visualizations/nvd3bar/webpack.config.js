var path = require("path");
var root = path.join(__dirname, "static");
module.exports = {
    devtool: "source-map",
    entry: { nvd3: root + "/nvd3.js" },
    output: {
        path: root,
        filename: "bundle.js",
        libraryTarget: "amd"
    },
    resolve: {
        modules: [root]
    }
};