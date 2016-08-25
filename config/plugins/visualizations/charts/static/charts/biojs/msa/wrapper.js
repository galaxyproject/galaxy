define( [ 'utils/utils' ], function( Utils ) {
    return Backbone.Model.extend({
        initialize: function( app, options ) {
            var chart = app.chart;
            var settings = chart.settings;
            var m = new msa.msa({
                el: $( '#'  + options.canvas_list[ 0 ] ),
                vis: {  conserv: settings.get( 'conserv' ) == 'true',
                        overviewbox: settings.get( 'overviewbox' ) == 'true' },
                menu: 'small',
                bootstrapMenu: settings.get( 'menu' ) == 'true'
            });
            m.u.file.importURL( options.dataset.download_url, function() {
                m.render();
                app.chart.state( 'ok', 'Chart drawn.' );
                options.process.resolve();
            });
        }
    });
});