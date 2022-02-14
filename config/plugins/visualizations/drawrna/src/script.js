import DrawRNA from "./drawrnajs/drawrna";
window.bundleEntries = window.bundleEntries || {};
window.bundleEntries.load = function (options) {
    var chart = options.chart;
    var dataset = options.dataset;
    $.ajax({
        url: dataset.download_url,
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
