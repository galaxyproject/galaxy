define( [ 'utils/utils', 'mvc/visualization/visualization-model' ], function( Utils ) {
    return Backbone.Model.extend({
        defaults : {
            title           : '',
            type            : '',
            date            : null,
            state           : '',
            state_info      : '',
            modified        : false,
            dataset_id      : '',
            dataset_id_job  : ''
        },

        initialize: function( options, viz_options ) {
            this.groups         = new Backbone.Collection();
            this.settings       = new Backbone.Model();
            this.definition     = {};
            this.viz_options    = viz_options;
            console.debug( 'model::initialize() - Initialized with configuration:' );
            console.debug( viz_options );
        },

        reset: function() {
            this.clear().set({
                title       : 'New Chart',
                type        : '__first',
                dataset_id  : this.viz_options.dataset_id
            });
            this.settings.clear();
            this.groups.reset();
            this.groups.add( { id : Utils.uid() } );
        },

        state: function( value, info ) {
            this.set( { state : value, state_info : info } );
            this.trigger( 'set:state' );
            console.debug( 'model::state() - ' + info + ' (' + value + ')' );
        },

        /** Pack and save nested chart model */
        save: function( options ) {
            var self = this;
            options = options || {};
            var chart_dict = {
                attributes : this.attributes,
                settings   : this.settings.attributes,
                groups     : []
            };
            this.groups.each( function( group ) {
                chart_dict.groups.push( group.attributes );
            });
            var viz = new Visualization({
                id      : this.viz_options.visualization_id || undefined,
                type    : 'charts',
                title   : this.get( 'title' ) || '',
                config  : {
                    dataset_id  : this.viz_options.dataset_id,
                    chart_dict  : this.viz_options.chart_dict = chart_dict
                }
            });
            viz.save().then( function( response ) {
                if ( response && response.id ) {
                    self.viz_options.visualization_id = response.id;
                    options.success && options.success();
                    console.debug( 'model::save() - Received visualization id: ' + response.id );
                } else {
                    options.error && options.error();
                    console.debug( 'model::save() - Unrecognized response. Saving may have failed.' );
                }
            }).fail( function( response ) {
                options.error && options.error();
                console.debug( 'model::save() - Saving failed.' );
            });
            console.debug( 'model::save() - Saved with configuration:' );
            console.debug( this.viz_options );
        },

        /** Load nested models/collections from packed dictionary */
        load: function() {
            console.debug( 'model::load() - Attempting to load with configuration:' );
            console.debug( this.viz_options );
            var chart_dict = this.viz_options.chart_dict;
            if ( chart_dict && chart_dict.attributes ) {
                this.set( chart_dict.attributes );
                this.state( 'ok', 'Loading saved visualization...' );
                this.settings.set( chart_dict.settings );
                this.groups.reset();
                this.groups.add( chart_dict.groups );
                this.set( 'modified', false );
                console.debug( 'model::load() - Loading chart model ' + chart_dict.attributes.type + '.' );
                this.trigger( 'redraw' );
                return true;
            }
            console.debug( 'model::load() - Visualization attributes unavailable.' );
            return false;
        }
    });
});