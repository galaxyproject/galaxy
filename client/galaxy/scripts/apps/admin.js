var jQuery = require( 'jquery' ),
    $ = jQuery,
    GalaxyApp = require( 'galaxy' ).GalaxyApp,
    AdminPanel = require( './panels/admin-panel' ),
    Page = require( 'layout/page' );

window.app = function app( options, bootstrapped ){
    window.Galaxy = new GalaxyApp( options, bootstrapped );
    Galaxy.debug( 'admin app' );
    Galaxy.params = Galaxy.config.params;
    $(function(){
        Galaxy.page = new Page.View( _.extend( options, {
            Left : AdminPanel
        } ) );
    });
};