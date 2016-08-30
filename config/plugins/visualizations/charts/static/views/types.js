/** This class renders the chart type selection grid. */
define( [ 'utils/utils', 'mvc/ui/ui-misc', 'mvc/ui/ui-tabs' ], function( Utils, Ui, Tabs ) {
    return Backbone.View.extend({
        events : {
            'click .item'    : '_onclick',
            'dblclick .item' : '_ondblclick'
        },

        initialize : function( app, options ) {
            var self = this;
            this.app = app;
            this.options = Utils.merge( options, this.optionsDefault );
            this.tabs = new Tabs.View( {} );
            this.setElement( this.tabs.$el.addClass( 'charts-types' ) );
            this.render();
        },

        render: function() {
            var self = this;
            this.index = {};
            this.first = null;
            _.each( this.app.types, function( type, type_id ) {
                if ( !type.datatypes || type.datatypes.indexOf( self.app.dataset.file_ext ) != -1  ) {
                    _.each( type.keywords.split( ' ' ), function( keyword ) {
                        self.index[ keyword ] = self.index[ keyword ] || {};
                        self.index[ keyword ][ type.category ] = self.index[ keyword ][ type.category ] || {};
                        self.index[ keyword ][ type.category ][ type_id ] = type;
                        self.first = self.first || type_id;
                    });
                }
            });
            var filtered = [];
            _.each( this.app.keywords, function( d, i ) {
                var keyword = d.value;
                var categories = self.index[ keyword ];
                if ( _.size( categories ) > 0 ) {
                    var catset = { id: Utils.uid(), help: d.help, title: d.label, value: d.value, list: [] };
                    _.each( categories, function( category, category_header ) {
                        var subset = { title: category_header, list:[] };
                        _.each( category, function( type, type_id ) {
                            subset.list.push({
                                id      : type_id,
                                title   : ( type.zoomable ? '<span class="fa fa-search-plus"/>' : '' ) + type.title + ' (' + type.library + ')',
                                url     : remote_root + 'src/visualizations/' + self.app.split( type_id ) + '/logo.png'
                            });
                        });
                        subset.list.sort( function( a, b ) { return a.id < b.id ? -1 : 1; } );
                        catset.list.push( subset );
                    });
                    catset.list.sort( function( a, b ) { return a.title < b.title ? -1 : 1; } );
                    filtered.push( catset );
                }
            });
            var $base_set = $( '<div/>' );
            var $full_set = $( '<div/>' );
            _.each( filtered, function( d, i ) {
                var $el = $( '<div/>' ).addClass( 'charts-grid' );
                                       //.append( $( '<p/>' ).addClass( 'ui-form-info' ).html( '<b>' + d.title + ': </b>' + d.help ) );
                _.each( d.list, function( category, j ) {
                    var $category = self._templateHeader( { title: category.title } );
                    $el.append( $category );
                    _.each( category.list, function( type ) {
                        $el.append( self._templateType( type ) );
                    });
                });
                if ( d.value === 'default' ) {
                    $base_set.append( $el );
                } else {
                    $full_set.append( $el );
                }
            });
            this.tabs.delAll();
            $base_set.length > 0 && this.tabs.add( { id: Utils.uid(), $el: $base_set, title: 'Selected' } );
            $full_set.length > 0 && this.tabs.add( { id: Utils.uid(), $el: $full_set, title: 'Full set' } );
        },

        /** Set/Get selected chart type */
        value: function( new_value ) {
            if ( new_value == '__first' ) {
                new_value = this.first;
            }
            var before = this.$( '.current' ).attr( 'chart_id' );
            if ( new_value !== undefined ) {
                this.$( '.current' ).removeClass( 'current' );
                this.$( '[chart_id="' + new_value + '"]' ).addClass( 'current' );
            }
            var after = this.$( '.current' ).attr( 'chart_id' );
            if( after !== undefined ) {
                if ( after != before && this.options.onchange ) {
                    this.options.onchange( after );
                }
                return after;
            }
        },

        /** Add click handler */
        _onclick: function( e ) {
            this.value( $( e.target ).closest( '.item' ).attr( 'chart_id' ) );
        },

        /** Add double click handler */
        _ondblclick: function( e ) {
            this.options.ondblclick && this.options.ondblclick( this.value() );
        },

        /** Header template */
        _templateHeader: function( options ) {
            return  '<div class="header ui-margin-top">' +
                        '&bull; ' + options.title +
                    '<div>';
        },

        /* Chart type template with image */
        _templateType: function( options ) {
            return  '<div class="item" chart_id="' + options.id + '">' +
                        '<img class="image" src="' + options.url + '">' +
                        '<div class="title">' + options.title + '</div>' +
                    '<div>';
        }
    });
});
