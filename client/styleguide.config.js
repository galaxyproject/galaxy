const path = require("path");
const glob = require("glob");
const merge = require("webpack-merge");

let webpackConfig = require("./webpack.config.js");

const fileLoaderTest = /\.(png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot)(\?.*$|$)/;

// Clear existing .scss rule(s) out of webpack config, we need special handling
// here.
// TODO: reimplement using smart merge w/ replacement strategy via webpack-merge
webpackConfig.module.rules = webpackConfig.module.rules.filter(rule => {
    return rule.test.toString() != /\.scss$/.toString() && rule.test.toString() != fileLoaderTest.toString();
});

webpackConfig.module.rules.push({
    test: /\.scss$/,
    use: [
        {
            loader: "style-loader"
        },
        {
            loader: "css-loader"
        },
        {
            loader: "sass-loader",
            options: {
                sourceMap: true
            }
        }
    ]
});

const fileLoaderConfigRule = { rules: [{ test: fileLoaderTest, use: ["file-loader"] }] };

webpackConfig.module = merge.smart(webpackConfig.module, fileLoaderConfigRule);
webpackConfig.output.publicPath = "";

const sections = [];

glob("./galaxy/docs/galaxy-*.md", (err, files) => {
    files.forEach(file => {
        const name = file.match(/galaxy-(\w+).md/)[1];
        sections.push({ name: "Galaxy " + name, content: file });
    });
}),
    sections.push(
        ...[
            {
                name: "Basic Bootstrap Styles",
                content: "./galaxy/docs/bootstrap.md"
            }
            // This will require additional configuration
            // {
            //     name: 'Components',
            //     components: './galaxy/scripts/components/*.vue'
            // }
        ]
    );

module.exports = {
    webpackConfig,
    sections,
    require: ["./galaxy/style/scss/base.scss"]
};
