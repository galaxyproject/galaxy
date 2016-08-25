define( [ 'utils/utils' ], function( Utils ) {
    return Backbone.Model.extend({
        initialize: function( app, options ) {
            var chart = app.chart;
            var m = new msa.msa({
                el: $( '#'  + options.canvas_list[ 0 ] ),
                vis: { conserv: false, overviewbox: false },
                menu: 'small',
                bootstrapMenu: true
            });
            m.u.file.importURL( options.dataset.download_url, function() {
                m.render();
                app.chart.state( 'ok', 'Chart drawn.' );
                options.process.resolve();
            });
        }
    });
});