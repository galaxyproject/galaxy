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
            ok( page.$( '#' + panelId ).css( 'display' ) == panelVisible, ( panelVisible ? '' : 'No' ) + ' ' + panelId + ' panel found.' );
        });
    }

    test( "test center/right", function() {
        this.$container.empty();
        var page = new Page.View({
            Right   : Backbone.View.extend({
                initialize: function() {
                    this.setElement( $('<div/>') );
                    this.model = new Backbone.Model({});
                }
            })
        }).render();
        _check( page, { left: 'none', right: 'block' } );
    });
    test( "test center", function() {
        this.$container.empty();
        var page = new Page.View({}).render();
        _check( page, { left: 'none', right: 'none' } );
    });
    test( "test left/center", function() {
        this.$container.empty();
        var page = new Page.View({
            Left   : Backbone.View.extend({
                initialize: function() {
                    this.setElement( $('<div/>') );
                    this.model = new Backbone.Model({});
                }
            })
        }).render();
        _check( page, { left: 'block', right: 'none' } );
    });
});