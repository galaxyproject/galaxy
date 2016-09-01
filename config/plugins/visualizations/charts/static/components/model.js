define( [ 'utils/utils', 'mvc/visualization/visualization-model' ], function( Utils ) {
    return Backbone.Model.extend({
        defaults : {
            id              : null,
            title           : '',
            type            : '',
            date            : null,
            state           : '',
            state_info      : '',
            modified        : false,
            dataset_id      : '',
            dataset_id_job  : ''
        },

        initialize: function( options ) {
            this.vis_id      = options.id;
            this.groups      = new Backbone.Collection();
            this.settings    = new Backbone.Model();
            this.definition  = {};
        },

        reset: function() {
            this.set({
                title         : 'New Chart',
                type          : '__first',
                dataset_id    : this.get( 'config' ).dataset_id
            });
            this.settings.clear();
            this.groups.reset();
            this.groups.add( { id : Utils.uid() } );
        },

        state: function( value, info ) {
            this.set( { state : value, state_info : info } );
            this.trigger( 'set:state' );
            console.debug( 'Chart:state() - ' + info + ' (' + value + ')' );
        },

        /** Pack and save nested chart model */
        save: function() {
            var chart_dict = {
                attributes : this.attributes,
                settings   : this.settings.attributes,
                groups     : []
            };
            this.groups.each( function( group ) {
                chart_dict.groups.push( group.attributes );
            });
            var vis = new Visualization({
                id      : this.vis_id,
                type    : 'charts',
                title   : this.get( 'title' ) || '',
                config  : {
                    dataset_id  : this.get( 'dataset_id' ),
                    chart_dict  : chart_dict
                }
            });
            vis.save();
        },

        /** Load nested models/collections from packed dictionary */
        load: function() {
            var chart_dict = this.get( 'config' ).chart_dict;
            if ( chart_dict.attributes ) {
                this.set( chart_dict.attributes );
                this.state( 'ok', 'Loading saved visualization...' );
                this.settings.set( chart_dict.settings );
                this.groups.reset();
                this.groups.add( chart_dict.groups );
                this.set( 'modified', false );
                console.debug( 'Model::load() - Loading chart model ' + chart_dict.attributes.type + '.' );
                return true;
            }
            console.debug( 'Model::load() - Chart attributes unavailable.' );
            return false;
        }
    });
});