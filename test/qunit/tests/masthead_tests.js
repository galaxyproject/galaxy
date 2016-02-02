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
                'logo_src'                  : '../../../static/images/galaxyIcon_noText.png',
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

    test( 'tabs', function() {
        var tab = this.masthead.collection.findWhere( { id: 'analysis' } );
        var $tab = $( '#analysis' ).find( '.dropdown' );
        var $toggle = $tab.find( '.dropdown-toggle' );
        var $note = $tab.find( '.dropdown-note' );
        var $menu = $tab.find( 'ul' );
        ok( tab && $tab.length == 1, 'Found analysis tab' );
        tab.set( 'title', 'Analyze' );
        ok( $toggle.html() == 'Analyze', 'Correct title' );
        ok( tab.get( 'target' ) == '_parent', 'Correct initial target' );
        tab.set( 'target', '_target' );
        ok( $toggle.attr( 'target' ) == '_target', 'Correct test target' );
        ok( $tab.css( 'visibility' ) == 'visible', 'Tab visible' );
        tab.set( 'visible', false );
        ok( $tab.css( 'visibility' ) == 'hidden', 'Tab hidden' );
        tab.set( 'visible', true );
        ok( $tab.css( 'visibility' ) == 'visible', 'Tab visible, again' );
        ok( $toggle.attr( 'href' ) == Galaxy.root, 'Correct initial url' );
        tab.set( 'url', '_url' );
        ok( $toggle.attr( 'href' ) == '/_url', 'Correct test url' );
        tab.set( 'url', 'http://_url' );
        ok( $toggle.attr( 'href' ) == 'http://_url', 'Correct http url' );
        tab.set( 'tooltip', '_tooltip' );
        $toggle.trigger( 'mouseover' );
        ok( $( '.tooltip-inner' ).html() == '_tooltip', 'Correct tooltip' );
        tab.set( 'tooltip', null );
        $toggle.trigger( 'mouseover' );
        ok( $( '.tooltip-inner' ).length == 0, 'Tooltip removed' );
        tab.set( 'tooltip', '_tooltip_new' );
        $toggle.trigger( 'mouseover' );
        ok( $( '.tooltip-inner' ).html() == '_tooltip_new', 'Correct new tooltip' );
        tab.set( 'cls', '_cls' );
        ok( $toggle.hasClass ( '_cls' ), 'Correct extra class' );
        tab.set( 'cls', '_cls_new' );
        ok( $toggle.hasClass ( '_cls_new' ) && !$toggle.hasClass ( '_cls' ), 'Correct new extra class' );
        ok( $note.html() == '', 'Correct empty note' );
        tab.set( { 'note' : '_note', 'show_note' : true } );
        ok( $note.html() == '_note', 'Correct new note' );
        tab.set( 'toggle', true );
        ok( $toggle.hasClass( 'toggle' ), 'Toggled' );
        tab.set( 'toggle', false );
        ok( !$toggle.hasClass( 'toggle' ), 'Untoggled' );
        tab.set( 'disabled', true );
        ok( $tab.hasClass( 'disabled' ), 'Correctly disabled' );
        tab.set( 'disabled', false );
        ok( !$tab.hasClass( 'disabled' ), 'Correctly enabled' );
        ok( $tab.hasClass( 'active' ), 'Highlighted' );
        tab.set( 'active', false );
        ok( !$tab.hasClass( 'active' ), 'Not highlighted' );
        tab.set( 'active', true );
        ok( $tab.hasClass( 'active' ), 'Highlighted, again' );
        tab.set( 'menu', [ { title: '_menu_title', url: '_menu_url', target: '_menu_target' } ] );
        ok( $menu.hasClass( 'dropdown-menu' ), 'Menu has correct class' );
        ok( $menu.css( 'display' ) == 'none', 'Menu hidden' );
        $toggle.trigger( 'click' );
        ok( $menu.css( 'display' ) == 'block', 'Menu shown' );
        var $item = $menu.find( 'a' );
        ok( $item.length == 1, 'Added one menu item' );
        ok( $item.html() == '_menu_title', 'Menu item has correct title' );
        ok( $item.attr( 'href' ) == '/_menu_url', 'Menu item has correct url' );
        ok( $item.attr( 'target' ) == '_menu_target', 'Menu item has correct target' );
        tab.set( 'menu', null );
        $item = $menu.find( 'a' );
        ok( $item.length == 0, 'All menu items removed' );
        tab.set( 'menu', [ { title: '_menu_title_0', url: '_menu_url_0', target: '_menu_target_0' },
                           { title: '_menu_title_1', url: '_menu_url_1', target: '_menu_target_1' } ] );
        $item = $menu.find( 'a' );
        ok( $item.length == 2, 'Two menu items added' );
        tab.set( 'show_menu', false );
        ok( $menu.css( 'display', 'none' ), 'Menu manually hidden' );
        tab.set( 'show_menu', true );
        ok( $menu.css( 'display', 'block' ), 'Menu manually shown, again' );
        var tab = this.masthead.collection.findWhere( { id: 'enable-scratchbook' } );
        var $tab = $( '#enable-scratchbook' ).find( '.dropdown' );
        ok( tab && $tab.length == 1, 'Found tab to enable scratchbook' );
        var $toggle = $tab.find( '.dropdown-toggle' );
        ok( !$toggle.hasClass( 'toggle' ), 'Untoggled before click' );
        $toggle.trigger( 'click' );
        ok( $toggle.hasClass( 'toggle' ), 'Toggled after click' );
        ok( Galaxy.frame.active, 'Scratchbook is active' );
    } );
});