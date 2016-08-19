/** This class renders the chart type selection grid. */
define( [ 'utils/utils', 'mvc/ui/ui-misc' ], function( Utils, Ui ) {
    return Backbone.View.extend({
        optionsDefault: {
            onchange    : null,
            ondblclick  : null
        },

        data: [ { label: 'Default', value: 'default',
                  help: 'The visualizations below were curated from different libraries. Its a representative set covering most use cases. Use this selection by default.' },
                { label: 'NVD3',    value: 'nvd3',
                  help: 'NVD3 is a popular d3-based library hosted at <a href="http://www.nvd3.org">www.nvd3.org<a/>. Most visualization types support intuitive drag-and-drop zooming and scaling. NVD3 generates high quality vector graphics. As with all vector based plugins, you may experience a slow down in browser responsiveness if visualizing thousands of data points.' },
                { label: 'jqPlot',  value: 'jqplot',
                  help: 'jqPlot is a canvas-based library hosted at www.jqplot.com.' },
                { label: 'Others',  value: 'others',
                  help: 'These visualizations were developed by the Galaxy team.' } ],

        events : {
            'click'     : '_onclick',
            'dblclick'  : '_ondblclick'
        },

        initialize : function( app, options ) {
            var self = this;
            this.app = app;
            this.options = Utils.merge( options, this.optionsDefault );
            this.library = new Ui.RadioButton.View({
                data    : this.data,
                onchange: function( value ) {
                    self._filter( value );
                    var data = _.findWhere( self.data, { value: value } );
                    self.$message.html( data.help );
                }
            });
            this.setElement( $( '<div/>' ).addClass( 'charts-grid' )
                                          .append( ( new Ui.Label( { title : 'Which visualization library would you like to use?' } ) ).$el )
                                          .append( this.library.$el.addClass( 'ui-margin-bottom' ) )
                                          .append( this.$message = $( '<div/>' ).addClass( 'ui-form-info ui-margin-bottom' ) ) );
            this._render();
            this.library.value( 'default' );
            this.library.trigger( 'change' );
        },

        /** Set/Get selected chart type */
        value: function( new_value ) {
            var before = this.$( '.current' ).attr( 'id' );
            if ( new_value !== undefined ) {
                this.$( '.current' ).removeClass( 'current' );
                this.$( '#' + new_value ).addClass( 'current' );
            }
            var after = this.$( '.current' ).attr( 'id' );
            if( after !== undefined ) {
                if ( after != before && this.options.onchange ) {
                    this.options.onchange( new_value );
                }
                return after;
            }
        },

        /** Filter chart types */
        _filter: function( value ) {
            this.$( '.header' ).hide();
            var types = this.app.types.attributes;
            for ( var id in types ) {
                var type = types[ id ];
                var $el = this.$( '#' + id );
                var $header = this.$( '#types-header-' + this.categories_index[ type.category ] );
                var keywords = type.keywords || '';
                if ( keywords.indexOf( value ) >= 0 ) {
                    $el.show();
                    $header.show();
                } else {
                    $el.hide();
                }
            }
        },

        /** Render chart type view */
        _render: function() {
            var category_index = 0;
            this.categories = {};
            this.categories_index = {};
            var types = this.app.types.attributes;
            for ( var id in types ) {
                var type = types[ id ];
                var category = type.category;
                if ( !this.categories[ category ] ) {
                    this.categories[ category ] = {};
                    this.categories_index[ category ] = category_index++;
                }
                this.categories[ category ][ id ] = type;
            }

            // add categories and charts to screen
            for (var category in this.categories) {
                var $el = $( '<div style="clear: both;"/>' ).append( this._template_header({
                              id    : 'types-header-' + this.categories_index[ category ],
                              title : category
                          }));
                for ( var id in this.categories[ category ] ) {
                    var type = this.categories[ category ][ id ];
                    var title = type.title + ' (' + type.library + ')';
                    if ( type.zoomable ) {
                        title = '<span class="fa fa-search-plus"/>' + title;
                    }
                    $el.append( this._template_item({
                        id      : id,
                        title   : title,
                        url     : config.app_root + 'charts/' + this.app.chartPath( id ) + '/logo.png'
                    }));
                }
                this.$el.append( $el );
            }
        },

        /** Add click handler */
        _onclick: function( e ) {
            var old_value = this.value();
            var new_value = $( e.target ).closest( '.item' ).attr( 'id' );
            if ( new_value != '' ) {
                if ( new_value && old_value != new_value ) {
                    this.value( new_value );
                }
            }
        },

        /** Add double click handler */
        _ondblclick: function( e ) {
            var value = this.value();
            if ( value && this.options.ondblclick ) {
                this.options.ondblclick( value );
            }
        },

        // header template
        _template_header: function( options ) {
            return  '<div id="' + options.id + '" class="header">' +
                        '&bull; ' + options.title +
                    '<div>';
        },

        // item template
        _template_item: function( options ) {
            return  '<div id="' + options.id + '" class="item">' +
                        '<img class="image" src="' + options.url + '">' +
                        '<div class="title">' + options.title + '</div>' +
                    '<div>';
        }
    });
});
