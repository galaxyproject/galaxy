define(['utils/utils', 'mvc/history/options-menu', 'mvc/history/history-panel-edit-current'],
    function( Utils, optionsMenu, HistoryPanel) {

    // history panel builder
    return Backbone.View.extend({
        initialize: function(options) {
            this.options = Utils.merge(options, {});
            this.setElement( this._template() );
            this.$( '#history-refresh-button' ).on( 'click', function() {
                if( top.Galaxy && top.Galaxy.currHistoryPanel ){
                    top.Galaxy.currHistoryPanel.loadCurrentHistory();
                }
            });
            var popupmenu = optionsMenu( this.$( '#history-options-button' ), {
                    anonymous    : options.user.valid && 'true' || 'false',
                    purgeAllowed : Galaxy.config.allow_user_dataset_purge && 'true' || 'false',
                    root         : Galaxy.root
                });
            Galaxy.historyOptionsMenu = popupmenu;
            var currPanel = new HistoryPanel.CurrentHistoryPanel({
                el              : this.$( '#current-history-panel' ),
                purgeAllowed    : Galaxy.config.allow_user_dataset_purge,
                linkTarget      : 'galaxy_main',
                $scrollContainer: function(){ return this.$el.parent(); }
            });
            currPanel.connectToQuotaMeter( Galaxy.quotaMeter );
            currPanel.listenToGalaxy( Galaxy );
            currPanel.loadCurrentHistory();
            Galaxy.currHistoryPanel = currPanel;
            var rp = new Panel( {
                panel   : this.$( '#right' ),
                center  : this.$( '#center' ),
                drag    : this.$( '#right > .unified-panel-footer > .drag' ),
                toggle  : this.$( '#right > .unified-panel-footer > .panel-collapse' ),
                right   : true
            } );
        },

        _template: function() {
            return  '<div id="right">' +
                        '<div class="unified-panel-header" unselectable="on">' +
                            '<div class="unified-panel-header-inner history-panel-header">' +
                                '<div style="float: right">' +
                                    '<a id="history-refresh-button" class="panel-header-button" href="javascript:void(0)" title="Refresh history">' +
                                        '<span class="fa fa-refresh"/>' +
                                    '</a>' +
                                    '<a id="history-options-button" class="panel-header-button" href="' + Galaxy.root + 'root/history_options" target="galaxy_main" title="History options">' +
                                        '<span class="fa fa-cog"/>' +
                                    '</a>' +
                                    '<a id="history-view-multi-button" class="panel-header-button" href="' + Galaxy.root + 'history/view_multiple" title="View all histories">' +
                                        '<span class="fa fa-columns"/>' +
                                    '</a>' +
                                '</div>' +
                                '<div class="panel-header-text">History</div>' +
                            '</div>' +
                        '</div>' +
                        '<div class="unified-panel-body">' +
                            '<div id="current-history-panel" class="history-panel"/>' +
                        '</div>' +
                        '<div class="unified-panel-footer">' +
                            '<div class="panel-collapse right"/>' +
                            '<div class="drag"/>' +
                        '</div>' +
                    '</div>';
        }
    });
});
