/* global define */
define([ "test-app", "mvc/ui/ui-misc", "mvc/ui/ui-popover", "QUnit"
], function( testApp, Ui, Popover, QUnit ){
    "use strict";
    Ui = Ui.default;
    Popover = Popover.default;
    QUnit.module( "Popover test", {
        beforeEach: function() {
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
        afterEach: function() {
            testApp.destroy();
        }
    } );

    QUnit.test( "test popover visibility", function( assert ) {
        assert.ok( this.popover.$el.css( 'display' ) == 'none', 'Popover is hidden.' );
        this.button.$el.trigger( 'click' );
        assert.ok( this.popover.$el.css( 'display' ) == 'block', 'Popover is shown.' );
        assert.ok( this.popover.$el.hasClass( 'bottom' ), 'Popover at bottom.' );
        this.popover.hide();
        assert.ok( this.popover.$el.css( 'display' ) == 'none', 'Popover is hidden manually.' );
        assert.ok( this.popover.$title.html() == 'Test Title', 'Initial title correct.' );
        this.popover.title( 'New Title' );
        assert.ok( this.popover.$title.html() == 'New Title', 'New title correct.' );
    } );
});
