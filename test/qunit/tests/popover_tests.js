/* global define, QUnit, module, test, ok, equal, deepEqual, notEqual */
define([ "test-app", "mvc/ui/ui-misc", "mvc/ui/ui-popover"
], function( testApp, Ui, Popover ){
    "use strict";
    module( "Popover test", {
        setup: function() {
            testApp.create();
            var self = this;
            this.button = new Ui.Button({
                title   : 'Test button',
                onclick : function() {
                    self.popover.show();
                }
            });
            this.$parent = $( '<div/>' ).append( this.button.$el );
            this.popover = new Popover.View({
                title       : 'Test Title',
                body        : 'Test Body',
                placement   : 'bottom',
                container   : this.button.$el
            });
            $( 'body' ).append( this.$parent );
        },
        teardown: function() {
            testApp.destroy();
        }
    } );

    test( "test popover visibility", function() {
        ok( this.popover.$el.css( 'display' ) == 'none', 'Popover is hidden.' );
        this.button.$el.trigger( 'click' );
        ok( this.popover.$el.css( 'display' ) == 'block', 'Popover is shown.' );
        ok( this.popover.$el.hasClass( 'bottom' ), 'Popover at bottom.' );
        this.popover.hide();
        ok( this.popover.$el.css( 'display' ) == 'none', 'Popover is hidden manually.' );
        ok( this.popover.$title.html() == 'Test Title', 'Initial title correct.' );
        this.popover.title( 'New Title' );
        ok( this.popover.$title.html() == 'New Title', 'New title correct.' );
    } );
});