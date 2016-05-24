/* global define, QUnit, module, test, ok, equal, deepEqual, notEqual */
define([ "test-app", "layout/page", "layout/panel",
], function( testApp, Page, Panel ){
    "use strict";
    module( "Page test", {
        setup: function() {
            testApp.create();
            $( 'body' ).append( this.$container = $( '<div/>' ).css( 'display', 'none' ) );
        },
        teardown: function() {
            testApp.destroy();
        }
    } );

    function _check( page, sidePanels ) {
        ok( page.$( '#center' ).length == 1, 'Center panel found.' );
        _.each( sidePanels, function( panelVisible, panelId ) {
            ok( page.$( '#' + panelId ).length == panelVisible ? 1 : 0, ( panelVisible ? '' : 'No' ) + ' ' + panelId + ' panel found.' );
            ok ( _.has( page, panelId ) == panelVisible, 'Panel attribute valid.' );
            panelVisible && ok( page.$( '#' + panelId ).find( '.panel-header-text' ).text() == '_title', 'Title correct' );
        });
    }

    test( "test center/right", function() {
        this.$container.empty();
        var page = new Page.PageLayoutView({
            el      : this.$container,
            center  : new Panel.CenterPanel({}),
            right   : new Panel.RightPanel({ title: '_title' })
        }).render();
        _check( page, { left: false, right: true } );
    });
    test( "test center", function() {
        this.$container.empty();
        var page = new Page.PageLayoutView({
            el      : this.$container,
            center  : new Panel.CenterPanel({})
        }).render();
        _check( page, { left: false, right: false } );
    });
    test( "test left/center", function() {
        this.$container.empty();
        var page = new Page.PageLayoutView({
            el      : this.$container,
            center  : new Panel.CenterPanel({}),
            left    : new Panel.LeftPanel({ title: '_title' })
        }).render();
        _check( page, { left: true, right: false } );
    });
});