// history panel builder
define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/history/options-menu', 'mvc/history/history-panel-edit-current'],
    function( Utils, Ui, optionsMenu, HistoryPanel) {
    return Backbone.View.extend({
        initialize: function(options) {
            this.options = Utils.merge( options, {} );
            this.setElement( this._template() );

            // build buttons
            var buttonRefresh = new Ui.ButtonLink({
                id      : 'history-refresh-button',
                title   : 'Refresh history',
                cls     : 'panel-header-button',
                icon    : 'fa fa-refresh',
                onclick : function() {
                    if( top.Galaxy && top.Galaxy.currHistoryPanel ) {
                        top.Galaxy.currHistoryPanel.loadCurrentHistory();
                    }
                }
            });
            var buttonOptions = new Ui.ButtonLink({
                id      : 'history-options-button',
                title   : 'History options',
                cls     : 'panel-header-button',
                target  : 'galaxy_main',
                icon    : 'fa fa-cog',
                href    : Galaxy.root + 'root/history_options'
            });
            var buttonViewMulti = new Ui.ButtonLink({
                id      : 'history-view-multi-button',
                title   : 'View all histories',
                cls     : 'panel-header-button',
                icon    : 'fa fa-columns',
                href    : Galaxy.root + 'history/view_multiple'
            });

            // define components (is used in app-view.js)
            this.components = {
                header  : {
                    title   : 'History',
                    buttons : [ buttonRefresh, buttonOptions, buttonViewMulti ]
                }
            }

            // build history options menu
            Galaxy.historyOptionsMenu = optionsMenu( buttonOptions.$el, {
                anonymous    : options.user.valid && 'true' || 'false',
                purgeAllowed : Galaxy.config.allow_user_dataset_purge && 'true' || 'false',
                root         : Galaxy.root
            });

            // load current history
            Galaxy.currHistoryPanel = new HistoryPanel.CurrentHistoryPanel({
                el              : this.$el,
                purgeAllowed    : Galaxy.config.allow_user_dataset_purge,
                linkTarget      : 'galaxy_main',
                $scrollContainer: function(){ return this.$el.parent(); }
            });
            Galaxy.currHistoryPanel.connectToQuotaMeter( Galaxy.quotaMeter );
            Galaxy.currHistoryPanel.listenToGalaxy( Galaxy );
            Galaxy.currHistoryPanel.loadCurrentHistory();
        },

        // body template
        _template: function() {
            return '<div id="current-history-panel" class="history-panel"/>';
        }
    });
});
