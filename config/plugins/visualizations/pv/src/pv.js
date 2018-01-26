import * as pv from "bio-pv";
_.extend(window.bundleEntries || {}, {
    load: function(options) {
        var settings = options.chart.settings;
        var viewer = pv.Viewer(document.getElementById(options.targets[0]), {
            quality: settings.get('quality'),
            width: 'auto',
            height: 'auto',
            antialias: true,
            outline: true
        });
        $.ajax( {
            url: options.dataset.download_url,
            cache: true,
            success: function(response) {
                var structure = pv.io.pdb(response);
                var viewer_options = {};
                _.each(settings.attributes, function(value, key) {
                    viewer_options[key.replace('viewer|', '')] = value;
                });
                viewer.clear();
                viewer.renderAs('protein', structure, viewer_options.mode, viewer_options);
                viewer.centerOn(structure);
                viewer.autoZoom();
                options.chart.state('ok', 'Chart drawn.');
                options.process.resolve();
            },
            error: function() {
                options.chart.state('ok', 'Failed to load pdb file.');
                options.process.resolve();
            }
        });
        $(window).resize(function() { viewer.fitParent() });
    }
});
