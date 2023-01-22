import DrawRNA from "./drawrnajs/drawrna";
window.bundleEntries = window.bundleEntries || {};

/* This will be part of the charts/viz standard lib in 23.1 */
const slashCleanup = /(\/)+/g;
function prefixedDownloadUrl(root, path) {
    return `${root}/${path}`.replace(slashCleanup, "/");
}

window.bundleEntries.load = function (options) {
    var chart = options.chart;
    var dataset = options.dataset;
    $.ajax({
        url: prefixedDownloadUrl(options.root, dataset.download_url),
        success: function(response) {
            var input = response.split('\n');
            var app = new DrawRNA({
                el: document.getElementById(options.target),
                seq: input[1],
                dotbr: input[2],
                resindex: false
            });
            app.render();
            chart.state('ok', 'Done.');
            options.process.resolve();
        },
        error: function() {
            chart.state('failed', 'Could not access dataset content of \'' + dataset.name + '\'.');
            options.process.resolve();
        }
    });
}
