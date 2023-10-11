import "./msa.min.js";

/* This will be part of the charts/viz standard lib in 23.1 */
const slashCleanup = /(\/)+/g;
function prefixedDownloadUrl(root, path) {
    return `${root}/${path}`.replace(slashCleanup, "/");
}

Object.assign(window.bundleEntries || {}, {
    load: function (options) {
        const chart = options.chart;
        const dataset = options.dataset;
        const settings = chart.settings;
        const msaViz = msa({
            el: $("#" + options.target),
            vis: {
                conserv: "true" == settings.get("conserv"),
                overviewbox: "true" == settings.get("overviewbox"),
            },
            menu: "small",
            bootstrapMenu: "true" == settings.get("menu"),
        });
        msaViz.u.file.importURL(prefixedDownloadUrl(options.root, dataset.download_url), () => {
            msaViz.render();
            chart.state("ok", "Chart drawn.");
            options.process.resolve();
        });
    },
});
