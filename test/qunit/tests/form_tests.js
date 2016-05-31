/* global define, QUnit, module, test, ok, equal, deepEqual, notEqual */
define([ 'test-app', 'mvc/form/form-input', 'mvc/ui/ui-misc', 'mvc/form/form-data', 'mvc/tool/tool-form', 'utils/utils',
], function( testApp, InputElement, Ui, FormData, ToolForm, Utils ){
    'use strict';
    module( 'Form test', {
        setup: function() {
            testApp.create();
        },
        teardown: function() {
            testApp.destroy();
        }
    } );

    test( 'tool-form', function() {
        var form = new ToolForm.View( { id: 'test' } );
        $( 'body' ).prepend( form.$el );
        window.fakeserver.respond();
        ok( form.$( '.portlet-title-text' ).html() == '<b>_name</b> _description (Galaxy Version _version)', 'Title correct' );
        var tour_ids = [];
        $( '[tour_id]' ).each( function() { tour_ids.push( $( this ).attr( 'tour_id' ) ) } );
        ok( JSON.stringify( tour_ids ) == '["a","b|c"]', 'Tour ids correct' );
        ok( JSON.stringify( form.data.create() ) == '{"a":"","b|c":null}', 'Created data correct' );
        var mapped_ids = [];
        form.data.matchModel( form.options, function( input, id ) { mapped_ids.push( $( '#' + id ).find( '[tour_id]' ).first().attr( 'tour_id' ) ) } );
        ok( JSON.stringify( mapped_ids ) == '["a","b|c"]', 'Remapped tour ids correct' );
        this.clock.tick ( window.WAIT_FADE );
        var dropdown = form.$( '#menu > .dropdown-menu' );
        ok( dropdown.children().length == 2, 'Found two menu items' );
        dropdown.find( '.fa-info-circle' ).parent().click();
        this.clock.tick ( window.WAIT_FADE );
        ok( form.$( '.ui-message' ).html() === '<span>This tool requires req_name_a (Version req_version_a) and req_name_b (Version req_version_b). Click <a target="_blank" href="https://wiki.galaxyproject.org/Tools/Requirements">here</a> for more information.</span>', 'Check requirements message' );
        this.clock.tick ( window.WAIT_FADE );
    });

    test( 'data', function() {
        var visits = [];
        Utils.get( { url: Galaxy.root + 'api/tools/test/build', success: function( response ) {
            FormData.visitInputs( response.inputs, function( node, name, context ) {
                visits.push( { name: name, node: node } );
            } );
        } } );
        window.fakeserver.respond();
        ok( JSON.stringify( visits ) == '[{"name":"a","node":{"name":"a","type":"text"}},{"name":"b|c","node":{"name":"c","type":"select","value":"h"}},{"name":"b|i","node":{"name":"i","type":"text"}},{"name":"b|j","node":{"name":"j","type":"text"}},{"name":"k_0|l","node":{"name":"l","type":"text"}},{"name":"k_0|m|n","node":{"name":"n","type":"select","value":"o"}},{"name":"k_0|m|p","node":{"name":"p","type":"text"}},{"name":"k_0|m|q","node":{"name":"q","type":"text"}}]', 'Testing value visitor' );
    });

    test( 'input', function() {
        var input = new InputElement( {}, {
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
        input.model.set( 'backdrop', true );
        ok( input.$backdrop.css( 'display' ) == 'block', 'Backdrop shown' );
        ok( input.$backdrop.css( 'opacity' ) == 0, 'Backdrop transparent' );
        ok( input.$backdrop.css( 'cursor' ) == 'default', 'Backdrop regular cursor' );
        input.model.set( 'backdrop', false );
        ok( input.$backdrop.css( 'display' ) == 'none', 'Backdrop hidden, again' );
        input.model.set( 'disabled', true );
        ok( input.$field.css( 'display' ) == 'none', 'Input field hidden' );
        input.model.set( 'disabled', false );
        this.clock.tick ( window.WAIT_FADE );
        ok( input.$field.css( 'display' ) == 'block', 'Input field shown, again' );
        this.clock.tick ( window.WAIT_FADE );
        input.model.set( 'color', 'red' );
        ok( input.$field.children().first().css( 'color' ) == 'rgb(255, 0, 0)', 'Shows correct new color' );
        input.model.set( 'color', null );
        ok( input.$field.children().first().css( 'color' ) == 'rgb(85, 85, 85)', 'Shows correct old color' );
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