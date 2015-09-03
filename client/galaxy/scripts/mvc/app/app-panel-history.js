define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/history/options-menu', 'mvc/history/history-panel-edit-current'],
    function( Utils, Ui, optionsMenu, HistoryPanel) {

    // history panel builder
    return Backbone.View.extend({
        initialize: function(options) {
            this.options = Utils.merge(options, {});
            this.setElement( this._template() );
            var popupmenu = optionsMenu( this.$( '#history-options-button' ), {
                    anonymous    : options.user.valid && 'true' || 'false',
                    purgeAllowed : Galaxy.config.allow_user_dataset_purge && 'true' || 'false',
                    root         : Galaxy.root
                });
            Galaxy.historyOptionsMenu = popupmenu;
            var currPanel = new HistoryPanel.CurrentHistoryPanel({
                el              : this.$el,
                purgeAllowed    : Galaxy.config.allow_user_dataset_purge,
                linkTarget      : 'galaxy_main',
                $scrollContainer: function(){ return this.$el.parent(); }
            });

            this.components = {
                header  : {
                    title   : 'History',
                    buttons : [new Ui.ButtonLink({
                            id      : 'history-refresh-button',
                            title   : 'Refresh history',
                            cls     : 'panel-header-button',
                            icon    : 'fa fa-refresh',
                            onclick : function() {
                                if( top.Galaxy && top.Galaxy.currHistoryPanel ) {
                                    top.Galaxy.currHistoryPanel.loadCurrentHistory();
                                }
                            }
                        })
                    ]
                }
            }

            currPanel.connectToQuotaMeter( Galaxy.quotaMeter );
            currPanel.listenToGalaxy( Galaxy );
            currPanel.loadCurrentHistory();
            Galaxy.currHistoryPanel = currPanel;
        },

        _template: function() {
            return '<div id="current-history-panel" class="history-panel"/>';
        },

        /*_template: function() {
            return  '<div class="unified-panel">' +
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
                        '<div class="unified-panel-footer"/>' +
                    '</div>';
        }*/
    });
});
