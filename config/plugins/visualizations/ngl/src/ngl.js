import * as ngl from "./viewer";

/** Get boolean as string */
function asBoolean (value) {
    return String(value).toLowerCase() == "true";
}

window.bundleEntries = window.bundleEntries || {};
window.bundleEntries.load = function (options) {
    var dataset = options.dataset,
        settings = options.chart.settings,
        stage = new ngl.Stage(options.target, { backgroundColor: settings.get("backcolor") }),
        representation_parameters = {},
        stage_parameters = {};
    representation_parameters = {
        radius: settings.get("radius"),
        assembly: settings.get("assembly"),
        color: settings.get("colorscheme"),
        opacity: settings.get("opacity"),
    };
    stage_parameters = { ext: dataset.extension, defaultRepresentation: true };
    try {
        stage.loadFile(dataset.download_url, stage_parameters).then(function (component) {
            component.addRepresentation(settings.get("mode"), representation_parameters);
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
