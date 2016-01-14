/* global define, QUnit, module, test, ok, equal, deepEqual, notEqual */
define([ "test-app", "layout/masthead"
], function( testApp, Masthead ){
    "use strict";
    module( "Masthead test", {
        setup: function() {
            testApp.create();
            var self = this;
            this.masthead = new Masthead.View({
                'brand'                     : 'brand',
                'use_remote_user'           : 'use_remote_user',
                'remote_user_logout_href'   : 'remote_user_logout_href',
                'lims_doc_url'              : 'lims_doc_url',
                'biostar_url'               : 'biostar_url',
                'biostar_url_redirect'      : 'biostar_url_redirect',
                'support_url'               : 'support_url',
                'search_url'                : 'search_url',
                'mailing_lists'             : 'mailing_lists',
                'screencasts_url'           : 'screencasts_url',
                'wiki_url'                  : 'wiki_url',
                'citation_url'              : 'citation_url',
                'terms_url'                 : 'terms_url',
                'logo_url'                  : 'logo_url',
                'is_admin_user'             : 'is_admin_user',
                'active_view'               : 'analysis',
                'ftp_upload_dir'            : 'ftp_upload_dir',
                'ftp_upload_site'           : 'ftp_upload_site',
                'datatypes_disable_auto'    : true,
                'allow_user_creation'       : true,
                'enable_cloud_launch'       : true,
                'user_requests'             : true
            });
            $( 'body' ).append( this.masthead.render().$el );
        },
        teardown: function() {
            testApp.destroy();
        }
    } );

    test( 'test masthead tabs', function() {
        this.tab = this.masthead.collection.first();
        this.$tab = $( '.dropdown:first' );
        this.$toggle = this.$tab.find( '.dropdown-toggle' );
        this.$note = this.$tab.find( '.dropdown-note' );
        this.$menu = this.$tab.find( 'ul' );
        this.tab.set( 'title', 'Analyze' );
        ok( this.$toggle.html() == 'Analyze', 'Correct title' );
        ok( this.tab.get( 'target' ) == '_parent', 'Correct initial target' );
        this.tab.set( 'target', '_target' );
        ok( this.$toggle.attr( 'target' ) == '_target', 'Correct test target' );
        ok( this.$tab.css( 'visibility' ) == 'visible', 'Tab visible' );
        this.tab.set( 'visible', false );
        ok( this.$tab.css( 'visibility' ) == 'hidden', 'Tab hidden' );
        this.tab.set( 'visible', true );
        ok( this.$tab.css( 'visibility' ) == 'visible', 'Tab visible, again' );
        ok( this.$toggle.attr( 'href' ) == Galaxy.root, 'Correct initial url' );
        this.tab.set( 'url', '_url' );
        ok( this.$toggle.attr( 'href' ) == '/_url', 'Correct test url' );
        this.tab.set( 'url', 'http://_url' );
        ok( this.$toggle.attr( 'href' ) == 'http://_url', 'Correct http url' );
        this.tab.set( 'tooltip', '_tooltip' );
        this.$toggle.trigger( 'mouseover' );
        ok( $( '.tooltip-inner' ).html() == '_tooltip', 'Correct tooltip' );
        this.tab.set( 'tooltip', null );
        this.$toggle.trigger( 'mouseover' );
        ok( $( '.tooltip-inner' ).length == 0, 'Tooltip removed' );
        this.tab.set( 'tooltip', '_tooltip_new' );
        this.$toggle.trigger( 'mouseover' );
        ok( $( '.tooltip-inner' ).html() == '_tooltip_new', 'Correct new tooltip' );
        this.tab.set( 'cls', '_cls' );
        ok( this.$toggle.hasClass ( '_cls' ), 'Correct extra class' );
        this.tab.set( 'cls', '_cls_new' );
        ok( this.$toggle.hasClass ( '_cls_new' ) && !this.$toggle.hasClass ( '_cls' ), 'Correct new extra class' );
        ok( this.$note.html() == '', 'Correct empty note' );
        this.tab.set( { 'note' : '_note', 'show_note' : true } );
        ok( this.$note.html() == '_note', 'Correct new note' );
        this.tab.set( 'toggle', true );
        ok( this.$toggle.hasClass( 'toggle' ), 'Toggled' );
        this.tab.set( 'toggle', false );
        ok( !this.$toggle.hasClass( 'toggle' ), 'Untoggled' );
        this.tab.set( 'disabled', true );
        ok( this.$tab.hasClass( 'disabled' ), 'Correctly disabled' );
        this.tab.set( 'disabled', false );
        ok( !this.$tab.hasClass( 'disabled' ), 'Correctly enabled' );
        ok( this.$tab.hasClass( 'active' ), 'Highlighted' );
        this.tab.set( 'active', false );
        ok( !this.$tab.hasClass( 'active' ), 'Not highlighted' );
        this.tab.set( 'active', true );
        ok( this.$tab.hasClass( 'active' ), 'Highlighted, again' );
        this.tab.set( 'menu', [ { title: '_menu_title', url: '_menu_url', target: '_menu_target' } ] );
        ok( this.$menu.hasClass( 'dropdown-menu' ), 'Menu has correct class' );
        ok( this.$menu.css( 'display' ) == 'none', 'Menu hidden' );
        this.$toggle.trigger( 'click' );
        ok( this.$menu.css( 'display' ) == 'block', 'Menu shown' );
        var $item = this.$menu.find( 'a' );
        ok( $item.length == 1, 'Added one menu item' );
        ok( $item.html() == '_menu_title', 'Menu item has correct title' );
        ok( $item.attr( 'href' ) == '/_menu_url', 'Menu item has correct url' );
        ok( $item.attr( 'target' ) == '_menu_target', 'Menu item has correct target' );
        this.tab.set( 'menu', null );
        $item = this.$menu.find( 'a' );
        ok( $item.length == 0, 'All menu items removed' );
        this.tab.set( 'menu', [ { title: '_menu_title_0', url: '_menu_url_0', target: '_menu_target_0' },
                                { title: '_menu_title_1', url: '_menu_url_1', target: '_menu_target_1' } ] );
        $item = this.$menu.find( 'a' );
        ok( $item.length == 2, 'Two menu items added' );
        this.tab.set( 'show_menu', false );
        ok( this.$menu.css( 'display', 'none' ), 'Menu manually hidden' );
        this.tab.set( 'show_menu', true );
        ok( this.$menu.css( 'display', 'block' ), 'Menu manually shown, again' );
    } );
});