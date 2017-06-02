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

    var LoginPage = Backbone.View.extend({
        initialize: function( page ) {
            this.page = page;
            this.model = new Backbone.Model({ title : _l( 'Login required' ) } );
            this.setElement( this._template() );
        },
        render: function() {
            this.page.$( '#galaxy_main' ).prop( 'src', options.welcome_url );
        },
        _template : function() {
            var login_url = options.root + 'user/login?' + $.param( { redirect : redirect } );
            return '<iframe src="' + login_url + '" frameborder="0" style="width: 100%; height: 100%;"/>';
        }
    });

    $(function(){
        Galaxy.page = new Page.View( _.extend( options, {
            Right : LoginPage
        } ) );
    });
};
