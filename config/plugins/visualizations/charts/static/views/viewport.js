/**
 *  The viewport creates and manages the dom elements used by the visualization plugins to draw the chart.
 *  Additionally, this class creates default request strings and request dictionaries parsed to the visualization plugins.
 *  This is the last class of the charts core classes before handing control over to the visualization plugins.
 */
define([ 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc', 'utils/utils' ],
        function( Portlet, Ui, Utils ) {
    return Backbone.View.extend({
        // list of container/canvas elements
        container_list: [],
        canvas_list: [],

        initialize: function( app, options ) {
            this.app = app;
            this.chart = this.app.chart;
            this.options = options;
            this.setElement( $( this._template() ) );

            // use full screen for viewer
            this._fullscreen( this.$el, 50 );

            // prevent window scrolling
            var initial_overflow = $( 'body' ).css( 'overflow' );
            this.$el.on( 'mouseover', function() {
                $( 'body' ).css( 'overflow', 'hidden' );
            }).on('mouseout', function() {
                $( 'body' ).css( 'overflow', initial_overflow );
            });

            // create container element
            this._createContainer( 'div' );

            // link redraw trigger
            var self = this;
            this.chart.on( 'redraw', function() {
                self.app.deferred.execute( function( process ) {
                    self._draw( process, self.chart );
                });
            });

            // link status handler
            this.chart.on( 'set:state', function() {
                var $info = self.$el.find( '#info' );
                var $container = self.$el.find( '.charts-viewport-container' );
                var $icon = $info.find( '#icon' );
                var $info_text = $info.find( '#text' );
                $icon.removeClass();
                $info.show();
                $info_text.html( self.chart.get( 'state_info' ) );
                var state = self.chart.get( 'state' );
                switch ( state ) {
                    case 'ok':
                        $info.hide();
                        $container.show();
                        break;
                    case 'failed':
                        $icon.addClass( 'icon fa fa-warning' );
                        $container.hide();
                        break;
                    default:
                        $icon.addClass( 'icon fa fa-spinner fa-spin' );
                        $container.show();
                }
            });
        },

        /** Show rendered chart */
        show: function() {
            this.$el.show();
        },

        /** Hide chart */
        hide: function() {
            this.$el.hide();
        },

        /** Force resize to fullscreen */
        _fullscreen: function( $el, margin ) {
            $el.css( 'height', $( window ).height() - margin );
            $( window ).resize( function() {
                $el.css( 'height', $( window ).height()  - margin );
            });
        },

        /** A chart may contain multiple sub charts/containers which are created here */
        _createContainer: function( tag, n ) {
            n = n || 1;
            for ( var i in this.container_list ) {
                this.container_list[ i ].remove();
            }
            this.container_list = [];
            this.canvas_list = [];
            for ( var i = 0; i < n; i++ ) {
                var container_el = $( this._templateContainer( tag, parseInt( 100 / n ) ) );
                this.$el.append( container_el );
                this.container_list[ i ] = container_el;
                this.canvas_list[ i ] = container_el.find( '.charts-viewport-canvas' ).attr( 'id' );
            }
        },

        /** Draws a new chart by loading and executing the corresponding chart wrapper */
        _draw: function( process, chart ) {
            var self = this;
            var chart_type = chart.get( 'type' );
            this.chart_definition = chart.definition;
            var n_panels = 1;
            if ( chart.settings.get( 'use_panels' ) === 'true' ) {
                n_panels = chart.groups.length;
            }
            this._createContainer( this.chart_definition.tag, n_panels );
            chart.state( 'wait', 'Please wait...' );
            if ( !this.chart_definition.execute || ( this.chart_definition.execute && chart.get( 'modified' ) ) ) {
                this.app.jobs.cleanup( chart );
                chart.set( 'modified', false );
            }
            require( [ 'plugin/charts/' + this.app.chartPath( chart_type ) + '/wrapper' ], function( ChartView ) {
                if ( self.chart_definition.execute ) {
                    self.app.jobs.request( chart, self._defaultSettingsString( chart ), self._defaultRequestString( chart ),
                        function() {
                            var view = new ChartView( self.app, {
                                process             : process,
                                chart               : chart,
                                request_dictionary  : self._defaultRequestDictionary( chart ),
                                canvas_list         : self.canvas_list
                            });
                        },
                        function() {
                            process.reject();
                        }
                    );
                } else {
                    var view = new ChartView( self.app, {
                        process             : process,
                        chart               : chart,
                        request_dictionary  : self._defaultRequestDictionary( chart ),
                        canvas_list         : self.canvas_list
                    });
                }
            });
        },

        //
        // REQUEST STRING FUNCTIONS
        //
        // create default chart request
        _defaultRequestString: function(chart) {
        
            // configure request
            var request_string = '';
            
            // add groups to data request
            var group_index = 0;
            var self = this;
            chart.groups.each(function(group) {
                // increase group counter
                group_index++;
                
                // add selected columns to column string
                for (var key in self.chart_definition.columns) {
                    request_string += key + '_' + group_index + ':' + (parseInt(group.get(key)) + 1) + ', ';
                }
            });
            
            // return
            return request_string.substring(0, request_string.length - 2);
        },
        
        // create default chart request
        _defaultSettingsString: function(chart) {
        
            // configure settings
            var settings_string = '';
            
            // add settings to settings string
            for (key in chart.settings.attributes) {
                settings_string += key + ':' + chart.settings.get(key) + ', ';
            };
            
            // return
            return settings_string.substring(0, settings_string.length - 2);
        },

        // create default chart request
        _defaultRequestDictionary: function(chart) {
        
            // configure request
            var request_dictionary = {
                groups : []
            };
            
            // update request dataset id
            if (this.chart_definition.execute) {
                request_dictionary.id = chart.get('dataset_id_job');
            } else {
                request_dictionary.id = chart.get('dataset_id');
            }
            
            // add groups to data request
            var group_index = 0;
            var self = this;
            chart.groups.each(function(group) {

                // add columns
                var columns = {};
                for (var column_key in self.chart_definition.columns) {
                    // get settings for column
                    var column_settings = self.chart_definition.columns[column_key];
                    
                    // add to columns
                    columns[column_key] = Utils.merge ({
                        index : group.get(column_key)
                    }, column_settings);
                }
                
                // add group data
                request_dictionary.groups.push({
                    key     : (++group_index) + ':' + group.get('key'),
                    columns : columns
                });
            });
            
            // return
            return request_dictionary;
        },
        
        // template
        _template: function() {
            return  '<div class="charts-viewport">' +
                        '<div id="info" class="info">' +
                            '<span id="icon" class="icon"/>' +
                            '<span id="text" class="text" />' +
                        '</div>' +
                    '</div>';
        },
        
        // template svg/div element
        _templateContainer: function(tag, width) {
            return  '<div class="charts-viewport-container" style="width:' + width + '%;">' +
                        '<div id="menu"/>' +
                        '<' + tag + ' id="' + Utils.uid() + '" class="charts-viewport-canvas">' +
                    '</div>';
        }
        
    });

});
