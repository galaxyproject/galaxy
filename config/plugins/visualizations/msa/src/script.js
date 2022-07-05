import './msa.min.js';

console.debug("MSA IS", msa);
Object.assign(window.bundleEntries || {}, {
    load: function (options) {
        console.debug('OPTIONS ARE', options);
        var r = options.chart,
            i = options.dataset,
            o = r.settings,
            s = msa({
                el: $("#" + options.target),
                vis: { conserv: "true" == o.get("conserv"), overviewbox: "true" == o.get("overviewbox") },
                menu: "small",
                bootstrapMenu: "true" == o.get("menu"),
            });
        s.u.file.importURL(i.download_url, function () {
            s.render(), r.state("ok", "Chart drawn."), options.process.resolve();
        });
    },
});
