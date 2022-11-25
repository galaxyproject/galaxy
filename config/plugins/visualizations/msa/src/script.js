import "./msa.min.js";

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
        const slash_cleanup = /(\/)+/g;
        const safe_download_url = `${options.root}/${dataset.download_url}`.replace(slash_cleanup, "/");
        msaViz.u.file.importURL(safe_download_url, () => {
            msaViz.render();
            chart.state("ok", "Chart drawn.");
            options.process.resolve();
        });
    },
});
