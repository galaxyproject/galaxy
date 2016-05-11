/* global define, QUnit, module, test, ok, equal, deepEqual, notEqual */
define([ 'test-app', 'mvc/form/form-input', 'mvc/ui/ui-misc',
], function( testApp, InputElement, Ui ){
    'use strict';
    module( 'Form test', {
        setup: function() {
            testApp.create();
        },
        teardown: function() {
            testApp.destroy();
        }
    } );

    test( 'input', function() {
        var input = new InputElement( null, {
            field: new Ui.Input({})
        });
        $( 'body' ).prepend( input.$el );
        ok( input.$field.css( 'display' ) == 'block', 'Input field shown' );
        ok( input.$preview.css( 'display' ) == 'none', 'Preview hidden' );
        ok( input.$collapsible.css( 'display' ) == 'none', 'Collapsible hidden' );
        ok( input.$title_text.css( 'display' ) == 'inline', 'Title visible' );
        ok( input.$title_text.html() == '', 'Title content unavailable' );
        input.model.set( 'label', '_label' );
        ok( input.$title_text.html() == '_label', 'Title content available' );
        ok( input.$error.css( 'display' ) == 'none', 'Error hidden' );
        input.model.set( 'error_text', '_error_text' );
        ok( input.$error.css( 'display' ) == 'block', 'Error visible' );
        ok( input.$error_text.html() == '_error_text', 'Error text correct' );
        input.model.set( 'error_text', null );
        ok( input.$error.css( 'display' ) == 'none', 'Error hidden, again' );
        ok( input.$backdrop.css( 'display' ) == 'none', 'Backdrop hidden' );
        input.model.set( 'backdrop', 'silent' );
        ok( input.$backdrop.css( 'display' ) == 'block', 'Backdrop shown' );
        ok( input.$backdrop.css( 'opacity' ) == 0, 'Backdrop transparent' );
        ok( input.$backdrop.css( 'cursor' ) == 'default', 'Backdrop regular cursor' );
        input.model.set( 'backdrop', 'default' );
        ok( input.$backdrop.css( 'opacity' ) > 0, 'Backdrop not transparent' );
        ok( input.$backdrop.css( 'cursor' ) == 'not-allowed', 'Backdrop blocked cursor' );
        input.model.set( 'backdrop', null );
        ok( input.$backdrop.css( 'display' ) == 'none', 'Backdrop hidden, again' );
        input.model.set( 'collapsible_value' , '_collapsible_value' );
        ok( input.$collapsible.css( 'display' ) == 'block', 'Collapsible field' );
        ok( input.$collapsible_text.html() == '_label', 'Title content available' );
        ok( input.$title_text.css( 'display' ) == 'none', 'Regular title not visible' );
        input.model.set( 'help', '_help' );
        ok( input.$info.html() == '_help', 'Correct help text' );
        input.model.set( 'argument', '_argument' );
        ok( input.$info.html() == '_help (_argument)', 'Correct help text with argument' );
        input.model.set( 'help', '_help (_argument)' );
        ok( input.$info.html() == '_help (_argument)', 'Correct help text with argument from help' );
    } );
});