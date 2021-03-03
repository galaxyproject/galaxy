const path = require("path");
const { getDocSections } = require("./docs/sections");
const buildWebpack = require("./webpack.config.js");

function getWebpack() {
    const cfg = buildWebpack();

    // looks like our src plays with the webpack publicPath dynamically,
    // presumably to allow for dyamic loads, but this is a problem when
    // you're not outputting code to a non-standard location.
    // allowing this to happen breaks the styleguide.
    cfg.module.rules.push({
        test: /onload\/publicPath/,
        use: { loader: "ignore-loader" },
    });

    return cfg;
}

// TODO: Fix broken module imports before attempting to view in styleguidef
const problemChildren = ["**/HistoryView.vue", "**/admin/DataManager/*", "**/LibraryFolder/*"];
if (problemChildren.length) {
    console.warn("Not rendering styleguide for the following components:", problemChildren);
}

function getSections() {
    // Style sections
    const docRootPath = path.join(__dirname, "docs/src");
    const { rootNode: docRoot } = getDocSections(docRootPath, { docSelector: "*.md" });
    const [design, styles] = docRoot.sections;
    delete docRoot.components;

    // recursive component tree docs
    const cmpPath = path.join(__dirname, "src/components");
    const { rootNode: componentDocs } = getDocSections(cmpPath, { ignore: problemChildren });

    return [design, styles, componentDocs];
}

module.exports = {
    webpackConfig: getWebpack(),
    title: "Galaxy Client Resources",
    sections: getSections(),
    getExampleFilename(componentPath) {
        return componentPath.replace(/\.(vue|js)?$/, ".md");
    },
    require: [
        "./src/style/scss/base.scss",
        "./src/polyfills.js",
        // "./src/bundleEntries.js"
    ],
    tocMode: "collapse",
    renderRootJsx: "./docs/root",
    styleguideDir: "./docs/dist",
    pagePerSection: true,
    ignore: problemChildren,
};
