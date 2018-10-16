_.extend(window.bundleEntries || {}, {
    load: function(options) {
        console.log(options);
        var self = this,
        chart    = options.chart,
        dataset  = options.dataset,
        settings = options.chart.settings,
        $.ajax({
            url     : dataset.download_url,
            success : function(content) {
                console.log(dataset);
                console.log(content); 
            },
            error: function() {
                chart.state( 'failed', 'Failed to access dataset.' );
                options.process.resolve();
            }
        });
    }
});
