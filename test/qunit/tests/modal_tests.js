/* global define, QUnit, module, test, ok, equal, deepEqual, notEqual */
define([ "test-app", "mvc/ui/ui-modal"
], function( testApp, GalaxyModal ){
    "use strict";
    module( "Modal dialog test", {
        setup: function() {
            testApp.create();
            var self = this;
            this.app = new GalaxyModal.View({
                title   : 'Test title',
                body    : 'Test body',
                buttons : {
                    'Ok' : function() {},
                    'Cancel' : function() { self.app.hide() }
                }
            });
        },
        teardown: function() {
            testApp.destroy();
        }
    } );

    test( "test dialog attributes", function() {
        ok( this.app.$header.find( '.title' ).html() == 'Test title', 'Modal header has correct title.');
        ok( this.app.$body.html() == 'Test body', 'Modal header has correct body.');
    } );

    test( "test dialog visibility", function() {
        ok( this.app.$el.css( 'display' ) == 'block', 'Modal is initially visible' );
        this.app.hide();
        this.clock.tick( WAIT_FADE );
        ok( this.app.$el.css( 'display' ) == 'none', 'Modal hidden manually' );
        this.app.show();
        this.clock.tick( WAIT_FADE );
        ok( this.app.$el.css( 'display' ) == 'block', 'Modal shown manually' );
        this.app.getButton( 'Ok' ).trigger( 'click' );
        this.clock.tick( WAIT_FADE );
        ok( this.app.$el.css( 'display' ) == 'block', 'Modal still visible after clicking Ok' );
        this.app.getButton( 'Cancel' ).trigger( 'click' );
        this.clock.tick( WAIT_FADE );
        ok( this.app.$el.css( 'display' ) == 'none', 'Modal hidden after clicking Cancel' );
        this.app.show();
        this.clock.tick( WAIT_FADE );
        ok( this.app.$el.css( 'display' ) == 'block', 'Modal manually shown again' );
        ok( !this.app.$header.hasClass( 'no-separator' ), 'Title separator tagged as visible.' );
        this.app.show({ title_separator: false });
        ok( this.app.$header.hasClass( 'no-separator' ), 'Title separator tagged as hidden.' );
        ok( this.app.$backdrop.hasClass( 'in' ), 'Backdrop tagged as shown.');
        this.app.show({ backdrop: false });
        ok( !this.app.$backdrop.hasClass( 'in' ), 'Backdrop tagged as hidden.');
    } );

    test( "test dialog closing events", function() {
        this.app.$backdrop.trigger( 'click' );
        this.clock.tick( WAIT_FADE );
        ok( this.app.$el.css( 'display' ) == 'block', 'Modal shown after backdrop click' );
        this.app.show({ closing_events: true });
        ok( this.app.$el.css( 'display' ) == 'block', 'Modal shown with closing events' );
        this.app.$backdrop.trigger( 'click' );
        this.clock.tick( WAIT_FADE );
        ok( this.app.$el.css( 'display' ) == 'none', 'Modal hidden after backdrop click' );
    } );

    test( "test dialog rendering", function() {
        var before = this.app.$el.html();
        this.app.render();
        ok( before == this.app.$el.html(), 'Re-rendering successful' );
        this.app.options.title = 'New Title';
        this.app.render();
        ok( this.app.$header.find( '.title' ).html() == 'New Title', 'Modal header has correct new title.' );
    });

    test( "test button states", function() {
        ok( this.app.getButton( 'Ok' ).html() === 'Ok', 'Ok has correct label' );
        ok( !this.app.getButton( 'Ok' ).prop( 'disabled' ), 'Ok is active' );
        ok( !this.app.getButton( 'Cancel' ).prop( 'disabled' ), 'Cancel is active' );
        this.app.disableButton( 'Ok' );
        ok( this.app.getButton( 'Ok' ).prop( 'disabled' ), 'Ok is disabled' );
        ok( !this.app.getButton( 'Cancel' ).prop( 'disabled' ), 'Cancel is still active' );
        this.app.disableButton( 'Cancel' );
        ok( this.app.getButton( 'Cancel' ).prop( 'disabled' ), 'Cancel is also disabled' );
        ok( this.app.getButton( 'Ok' ).prop( 'disabled' ), 'Ok is still disabled' );
        this.app.enableButton( 'Ok' );
        ok( this.app.getButton( 'Cancel' ).prop( 'disabled' ), 'Cancel is still disabled' );
        ok( !this.app.getButton( 'Ok' ).prop( 'disabled' ), 'Ok is active again' );
    } );
});