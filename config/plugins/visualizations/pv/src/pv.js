import * as pv from "bio-pv";

window.bundleEntries = window.bundleEntries || {};
window.bundleEntries.load = function (options) {
    var settings = options.chart.settings;
    var viewer = pv.Viewer(document.getElementById(options.target), {
        quality: settings.get("quality"),
        width: "auto",
        height: "auto",
        antialias: true,
        outline: true,
    });
    var xhr = new XMLHttpRequest();
    xhr.open("GET", options.dataset.download_url);
    xhr.onload = function () {
        if (xhr.status === 200) {
            var structure = pv.io.pdb(xhr.response);
            var viewer_options = {};
            for (const [key, value] of Object.entries(settings.attributes)) {
                viewer_options[key.replace("viewer|", "")] = value;
            }
            viewer.clear();
            viewer.renderAs("protein", structure, viewer_options.mode, viewer_options);
            viewer.centerOn(structure);
            viewer.autoZoom();
            options.chart.state("ok", "Chart drawn.");
            options.process.resolve();
        } else {
            options.chart.state("ok", "Failed to load pdb file.");
            options.process.resolve();
        }
    };
    xhr.send();
    window.onresize = function () {
        viewer.fitParent();
    };
};
