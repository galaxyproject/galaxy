
var jQuery = require( 'jquery' ),
    $ = jQuery,
    GalaxyApp = require( 'galaxy' ).GalaxyApp,
    PANEL = require( 'layout/panel' ),
    _l = require( 'utils/localization' ),
    PAGE = require( 'layout/page' );

window.app = function app( options, bootstrapped ){
    window.Galaxy = new GalaxyApp( options, bootstrapped );
    Galaxy.debug( 'login app' );
    var redirect = encodeURI( options.redirect );

    // TODO: remove iframe for user login (at least) and render login page from here
    // then remove this redirect
    if( !options.show_welcome_with_login ){
        var params = jQuery.param({ use_panels : 'True', redirect : redirect });
        window.location.href = Galaxy.root + 'user/login?' + params;
        return;
    }

    var loginPage = new PAGE.PageLayoutView( _.extend( options, {
        el      : 'body',
        center  : new PANEL.CenterPanel({ el : '#center' }),
        right   : new PANEL.RightPanel({
            title : _l( 'Login required' ),
            el : '#right'
        }),
    }));

    $(function(){
        // TODO: incorporate *actual* referrer/redirect info as the original page does
        var params = jQuery.param({ redirect : redirect }),
            loginUrl = Galaxy.root + 'user/login?' + params;
        loginPage.render();

        // welcome page (probably) needs to remain sandboxed
        loginPage.center.$( '#galaxy_main' ).prop( 'src', options.welcome_url );

        loginPage.right.$( '.unified-panel-body' )
            .css( 'overflow', 'hidden' )
            .html( '<iframe src="' + loginUrl + '" frameborder="0" style="width: 100%; height: 100%;"/>' );
    });
};
