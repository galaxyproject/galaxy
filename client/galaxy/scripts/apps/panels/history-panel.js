var Ui = require( 'mvc/ui/ui-misc' ),
    historyOptionsMenu = require( 'mvc/history/options-menu' );
    CurrentHistoryView = require( 'mvc/history/history-view-edit-current' ).CurrentHistoryView,
    _l = require( 'utils/localization' );

/** the right hand panel in the analysis page that shows the current history */
var HistoryPanel = Backbone.View.extend({

    initialize : function( page, options ) {
        var self = this;
        this.userIsAnonymous            = Galaxy.user.isAnonymous();
        this.allow_user_dataset_purge   = options.config.allow_user_dataset_purge;
        this.root                       = options.root;

        // view of the current history
        this.historyView = new CurrentHistoryView({
            className       : CurrentHistoryView.prototype.className + ' middle',
            purgeAllowed    : this.allow_user_dataset_purge,
            linkTarget      : 'galaxy_main'
        });

        // add history panel to Galaxy object
        Galaxy.currHistoryPanel = this.historyView;
        Galaxy.currHistoryPanel.listenToGalaxy( Galaxy );

        // build buttons
        this.buttonRefresh = new Ui.ButtonLink({
            id      : 'history-refresh-button',
            title   : 'Refresh history',
            cls     : 'panel-header-button',
            icon    : 'fa fa-refresh',
            onclick : function() {
                self.historyView.loadCurrentHistory();
            }
        });
        this.buttonOptions = new Ui.ButtonLink({
            id      : 'history-options-button',
            title   : 'History options',
            cls     : 'panel-header-button',
            target  : 'galaxy_main',
            icon    : 'fa fa-cog',
            href    : this.root + 'root/history_options'
        });
        this.buttonViewMulti = new Ui.ButtonLink({
            id      : 'history-view-multi-button',
            title   : 'View all histories',
            cls     : 'panel-header-button',
            icon    : 'fa fa-columns',
            href    : this.root + 'history/view_multiple'
        });

        // define components
        this.model = new Backbone.Model({
            cls     : 'history-right-panel',
            title   : _l( 'History' ),
            buttons : [ this.buttonRefresh, this.buttonOptions, this.buttonViewMulti ]
        });

        // build body template and connect history view
        this.setElement( this._template() );
        this.historyView.setElement( this.$el );
        this.historyView.connectToQuotaMeter( Galaxy.quotaMeter );
        this.historyView.loadCurrentHistory();

        // fetch to update the quota meter adding 'current' for any anon-user's id
        Galaxy.listenTo( this.historyView, 'history-size-change', function(){
            Galaxy.user.fetch({ url: Galaxy.user.urlRoot() + '/' + ( Galaxy.user.id || 'current' ) });
        });
    },

    render : function() {
        this.optionsMenu = historyOptionsMenu( this.buttonOptions.$el, {
            anonymous    : this.userIsAnonymous,
            purgeAllowed : this.allow_user_dataset_purge,
            root         : this.root
        });
        this.buttonViewMulti.$el[ !this.userIsAnonymous ? 'show' : 'hide' ]();
    },

    /** add history view div */
    _template : function( data ){
        return [
            '<div id="current-history-panel" class="history-panel middle"/>',
        ].join('');
    },

    toString : function() { return 'historyPanel' }
});

module.exports = HistoryPanel;
