/** This class renders the page list. */
define( [ 'utils/utils', 'mvc/grid/grid-view' ], function( Utils, GridView ) {
    var View = Backbone.View.extend({
        initialize: function( options ) {
            var self = this;
            this.setElement( $( '<div/>' ) );
            this.model = new Backbone.Model();
            Utils.get({
                url     : Galaxy.root + 'page/list',
                success : function( response ) {
                    response[ 'dict_format' ] = true;
                    self.model.set( response );
                    self.render();
                }
            });
        },

        render: function() {
            var grid = new GridView( this.model.attributes );
            this.$el.empty().append( grid.$el );
            this.$el.append( this._templateShared() );
        },

        _templateShared: function() {
            var $tmpl = $(  '<div>' +
                                '<h2>Pages shared with you by others</h2>' +
                            '</div>' );
            var options = this.model.attributes;
            if ( options.shared_by_others && options.shared_by_others.length > 0 ) {
                var $table = $( '<table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">' +
                                    '<tr class="header">' +
                                        '<th>Title</th>' +
                                        '<th>Owner</th>' +
                                    '</tr>' +
                                '</table>' );
                _.each( options.shared_by_others, function( page, index ) {
                    var display_url = Galaxy.root + 'page/display_by_username_and_slug?username=' + page.username + '&slug=' + page.slug;
                    $table.append(  '<tr>' +
                                        '<td>' +
                                            '<a href="' + display_url + '">' + _.escape( page.title ) + '</a>' +
                                        '</td>' +
                                        '<td>' + _.escape( page.username ) + '</td>' +
                                    '</tr>' );
                });
                $tmpl.append( $table );
            } else {
                $tmpl.append( 'No pages have been shared with you.' );
            }
            return $tmpl;
        }
    });

    return {
        View: View
    }
});