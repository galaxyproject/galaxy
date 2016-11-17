var RightPanel = require( 'layout/panel' ).RightPanel,
    Ui = require( 'mvc/ui/ui-misc' ),
    historyOptionsMenu = require( 'mvc/history/options-menu' );
    CurrentHistoryView = require( 'mvc/history/history-view-edit-current' ).CurrentHistoryView,
    _l = require( 'utils/localization' );

/** the right hand panel in the analysis page that shows the current history */
var HistoryPanel = RightPanel.extend({

    title : _l( 'History' ),

    initialize : function( options ){
        RightPanel.prototype.initialize.call( this, options );
        this.options = _.pick( options, 'userIsAnonymous', 'allow_user_dataset_purge', 'galaxyRoot' );

        // view of the current history
        this.historyView = new CurrentHistoryView({
            className       : CurrentHistoryView.prototype.className + ' middle',
            purgeAllowed    : options.allow_user_dataset_purge,
            linkTarget      : 'galaxy_main'
        });
    },

    /** override to change footer selector */
    $toggleButton : function(){
        return this.$( '.footer > .panel-collapse' );
    },

    render : function(){
        RightPanel.prototype.render.call( this );
        this.optionsMenu = historyOptionsMenu( this.$( '#history-options-button' ), {
            anonymous    : this.options.userIsAnonymous,
            purgeAllowed : this.options.allow_user_dataset_purge,
            root         : this.options.galaxyRoot
        });
        this.$( '> .header .buttons [title]' ).tooltip({ placement: 'bottom' });
        this.historyView.setElement( this.$( '.history-panel' ) );
        this.$el.attr( 'class', 'history-right-panel' );
    },

    /** override to add buttons */
    _templateHeader: function( data ){
        var historyUrl = this.options.galaxyRoot + 'history';
        var multiUrl = this.options.galaxyRoot + 'history/view_multiple';
        return [
            '<div class="header">',
                '<div class="buttons">',
                    // this button re-fetches the history and contents and re-renders the history panel
                    '<a id="history-refresh-button" title="', _l( 'Refresh history' ), '" ',
                       'class="" href="', historyUrl, '"><span class="fa fa-refresh"></span></a>',
                    // opens a drop down menu with history related functions (like view all, delete, share, etc.)
                    '<a id="history-options-button" title="', _l( 'History options' ), '" ',
                       'class="" href="javascript:void(0)"><span class="fa fa-cog"></span></a>',
                    !this.options.userIsAnonymous?
                        [ '<a id="history-view-multi-button" title="', _l( 'View all histories' ), '" ',
                             'class="" href="', multiUrl, '"><span class="fa fa-columns"></span></a>' ].join('') : '',
                '</div>',
                '<div class="title">', _.escape( this.title ), '</div>',
            '</div>',
        ].join('');
    },

    /** add history view div */
    _templateBody : function( data ){
        return [
            '<div id="current-history-panel" class="history-panel middle"/>',
        ].join('');
    },

    /** override to use simplified selector */
    _templateFooter: function( data ){
        return [
            '<div class="footer">',
                '<div class="panel-collapse ', _.escape( this.id ), '"/>',
                '<div class="drag"/>',
            '</div>',
        ].join('');
    },

    events : {
        'click #history-refresh-button'   : '_clickRefresh',
        // override to change footer selector
        'mousedown .footer > .drag'       : '_mousedownDragHandler',
        'click .footer > .panel-collapse' : 'toggle'
    },

    _clickRefresh : function( ev ){
        ev.preventDefault();
        this.historyView.loadCurrentHistory();
    },

    toString : function(){ return 'HistoryPanel'; }
});

module.exports = HistoryPanel;
