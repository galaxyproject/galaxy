var path = require("path");
var root = path.join(__dirname, "static");
module.exports = {
    devtool: "source-map",
    entry: { entry: root + "/entry.js" },
    output: {
        path: root,
        filename: "bundle.js",
        libraryTarget: "amd"
    },
    resolve: {
        modules: [root]
    }
};