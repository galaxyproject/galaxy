var jQuery = require( 'jquery' ),
    $ = jQuery,
    GalaxyApp = require( 'galaxy' ).GalaxyApp,
    _l = require( 'utils/localization' ),
    Page = require( 'layout/page' );

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

    var loginPage = new Page( _.extend( options, {
        right   : Backbone.View.extend({
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
