/** This class renders the grid list. */
define( [ 'utils/utils', 'mvc/grid/grid-view', 'mvc/history/history-model', 'mvc/history/copy-dialog' ], function( Utils, GridView, HistoryModel, historyCopyDialog ) {

    var View = Backbone.View.extend({
        title: "Histories",
        initialize: function( options ) {
            var self = this;
            this.setElement( $( '<div/>' ) );
            this.model = new Backbone.Model();
            Utils.get({
                url     : Galaxy.root + 'history/' + options.action_id,
                success : function( response ) {
                    response[ 'dict_format' ] = true;
                    _.each( response[ 'operations' ], function( operation ) {
                        if ( operation.label == 'Copy' ) {
                            operation.onclick = function( id ) { self._showCopyDialog( id ) };
                        }
                    });
                    self.model.set( response );
                    self.render();
                }
            });
        },

        render: function() {
            var grid = new GridView( this.model.attributes );
            this.$el.empty().append( grid.$el );
        },

        _showCopyDialog: function( id ) {
            var history = new HistoryModel.History( { id : id } );
            history.fetch()
                   .fail( function() {
                       alert( 'History could not be fetched. Please contact an administrator' );
                   })
                   .done( function(){
                       historyCopyDialog( history, {} ).done( function() {
                           if( window.parent && window.parent.Galaxy && window.parent.Galaxy.currHistoryPanel ) {
                               window.parent.Galaxy.currHistoryPanel.loadCurrentHistory();
                           }
                           window.location.reload( true );
                       } );
                   });
        }
    });

    return {
        View: View
    }
});
