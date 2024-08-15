import * as ngl from "./viewer";

/** Get boolean as string */
function asBoolean(value) {
    return String(value).toLowerCase() == "true";
}

/* This will be part of the charts/viz standard lib in 23.1 */
const slashCleanup = /(\/)+/g;
function prefixedDownloadUrl(root, path) {
    return `${root}/${path}`.replace(slashCleanup, "/");
}

window.bundleEntries = window.bundleEntries || {};
window.bundleEntries.load = function (options) {
    const dataset = options.dataset;
    const settings = options.chart.settings;
    const stage = new ngl.Stage(options.target, { backgroundColor: settings.get("backcolor") });
    const representationParameters = {
        radius: settings.get("radius"),
        assembly: settings.get("assembly"),
        color: settings.get("colorscheme"),
        opacity: settings.get("opacity"),
    };
    const stageParameters = { ext: dataset.extension, defaultRepresentation: true };

    try {
        stage
            .loadFile(prefixedDownloadUrl(options.root, dataset.download_url), stageParameters)
            .then(function (component) {
                component.addRepresentation(settings.get("mode"), representationParameters);
                options.chart.state("ok", "Chart drawn.");
                options.process.resolve();
            });
    } catch (e) {
        options.chart.state("failed", "Could not load PDB file.");
        options.process.resolve();
    }
    stage.setQuality(settings.get("quality"));
    const spin = String(settings.get("spin")).toLowerCase() == "true";
    if (spin) {
        stage.setSpin([0, 1, 0], 0.01);
    }
    // Re-renders the molecule view when window is resized
    window.onresize = function () {
        stage.handleResize();
    };
};
