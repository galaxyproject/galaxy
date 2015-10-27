
var GalaxyMasthead = require( '../galaxy.masthead' ).GalaxyMasthead,
    GalaxyMenu = require( '../galaxy.menu' ).GalaxyMenu,
    History = require( '../mvc/history/history-model' ).History,
    HistoryPanelEdit = require( '../mvc/history/history-panel-edit' ).HistoryPanelEdit;

//TODO: this doesn't address multiple apps per page
window.app = function app( options, bootstrapped ){
    if( !( Galaxy.masthead && Galaxy.menu ) ){
        // adapter to galaxy.masthead.mako config
        var mastheadConfig = _.extend( _.clone( Galaxy.config ), {
            user : {
                requests    : Galaxy.currUser.get( 'requests' ),
                email       : Galaxy.currUser.get( 'email' ),
                valid       : Galaxy.currUser.isAnonymous(),
                json        : Galaxy.currUser.toJSON()
            }
        });
        Galaxy.masthead = new GalaxyMasthead( mastheadConfig );
        Galaxy.menu = new GalaxyMenu({
            masthead    : Galaxy.masthead,
            config      : mastheadConfig
        });
        console.debug( Galaxy.masthead );
        console.debug( Galaxy.menu );
    }

    bootstrapped = bootstrapped || {};
    window.panel = new HistoryPanelEdit({
        show_deleted    : bootstrapped.show_deleted,
        show_hidden     : bootstrapped.show_deleted,
        purgeAllowed    : Galaxy.config.allow_user_dataset_purge,
        model           : new History( bootstrapped.history, bootstrapped.contents )
    });
    $(function(){
        panel.render().$el.appendTo( ( options || {} ).panelLoc || 'body' );
    });

    return panel;
};
