<<<<<<< HEAD
webpackJsonp([4],[function(e,r,n){(function(e){var r=n(1),a=r,i=n(59).GalaxyApp,o=n(11),t=n(5),l=n(61);window.app=function(n,c){window.Galaxy=new i(n,c),Galaxy.debug("login app");var d=encodeURI(n.redirect);if(!n.show_welcome_with_login){var w=r.param({use_panels:"True",redirect:d});return void(window.location.href=Galaxy.root+"user/login?"+w)}var p=new l.PageLayoutView(e.extend(n,{el:"body",center:new o.CenterPanel({el:"#center"}),right:new o.RightPanel({title:t("Login required"),el:"#right"})}));a(function(){var e=r.param({redirect:d}),a=Galaxy.root+"user/login?"+e;p.render(),p.center.$("#galaxy_main").prop("src",n.welcome_url),p.right.$(".unified-panel-body").css("overflow","hidden").html('<iframe src="'+a+'" frameborder="0" style="width: 100%; height: 100%;"/>')})}}).call(r,n(3))}]);
=======
webpackJsonp([5],[
/* 0 */
/*!**************************************!*\
  !*** ./galaxy/scripts/apps/login.js ***!
  \**************************************/
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function(_) {
	var jQuery = __webpack_require__( /*! jquery */ 3 ),
	    $ = jQuery,
	    GalaxyApp = __webpack_require__( /*! galaxy */ 4 ).GalaxyApp,
	    PANEL = __webpack_require__( /*! layout/panel */ 12 ),
	    _l = __webpack_require__( /*! utils/localization */ 7 ),
	    PAGE = __webpack_require__( /*! layout/page */ 98 );
	
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
	
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(/*! underscore */ 1)))

/***/ }
]);
>>>>>>> 3646d08... UI, history: more feedback on bad collection type
//# sourceMappingURL=login.bundled.js.map