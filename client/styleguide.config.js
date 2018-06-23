let path = require("path");

let webpackConfig = require("./webpack.config.js");

// We don't use webpack for our sass files in the main app, but use it here
// so we get rebuilds
webpackConfig.module.rules.push({
    test: /\.scss$/,
    use: [
        {
            loader: "style-loader"
        },
        {
            loader: "css-loader",
            options: {
                alias: {
                    "../images": path.resolve(__dirname, "../static/images"),
                    ".": path.resolve(__dirname, "../static/style/blue")
                }
            }
        },
        {
            loader: "sass-loader",
            options: {
                sourceMap: true
            }
        }
    ]
});

webpackConfig.module.rules.push({ test: /\.(png|jpg|gif|eot|ttf|woff|woff2|svg)$/, use: ["file-loader"] });

module.exports = {
    webpackConfig,
    sections: [
        {
            name: "Galaxy Styles",
            content: "./galaxy/docs/galaxy-styles.md"
        },
        {
            name: "Basic Bootstrap Styles",
            content: "./galaxy/docs/bootstrap.md"
        }
        // This will require additional configuration
        // {
        //   name: 'Components',
        //   content: 'galaxy/scripts/components/**/*.vue'
        // }
    ],
    require: ["./galaxy/style/scss/base.scss"]
};
