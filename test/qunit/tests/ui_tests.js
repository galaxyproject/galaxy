/* global define, QUnit, module, test, ok, equal, deepEqual, notEqual */
define([ 'test-app', 'mvc/ui/ui-misc', 'mvc/ui/ui-select-content',
], function( testApp, Ui, SelectContent ){
    'use strict';
    module( 'Ui test', {
    setup: function() {
            testApp.create();
        },
        teardown: function() {
            testApp.destroy();
        }
    } );

    test( 'label', function() {
        var label = new Ui.Label({
            title   : '_title'
        });
        $( 'body' ).prepend( label.$el );
        ok( label.$el.html() === '_title', 'Correct title' );
        label.model.set( 'title', '_new_title' );
        ok( label.$el.html() === '_new_title', 'Correct new title' );
    } );

    test( 'input', function() {
        var input = new Ui.Input();
        $( 'body' ).prepend( input.$el );
        ok( input.tagName === 'input', 'Created input.' );
        ok( input.value() === undefined, 'Input empty.' );
        input.model.set( 'value', '_value' );
        ok( input.$el.val() === '_value', 'Input with value.' );
        ok( !input.$el.hasClass( '_cls' ), 'Has no custom class.' );
        input.model.set( 'cls', '_cls' );
        ok( input.$el.hasClass( '_cls' ), 'Has custom class.' );
        ok( !input.$el.attr( 'placeholder' ), 'Has no placeholder' );
        input.model.set( 'placeholder', '_placeholder' );
        ok( input.$el.attr( 'placeholder' ) === '_placeholder', 'Has correct placeholder' );
        input.model.set( 'disabled', true );
        ok( input.$el.attr( 'disabled' ), 'Disabled' );
        input.model.set( 'disabled', false );
        ok( !input.$el.attr( 'disabled' ), 'Enabled' );
        input.model.set( 'visible', false );
        ok( input.$el.css( 'display' ) === 'none', 'Hidden' );
        input.model.set( 'visible', true );
        ok( input.$el.css( 'display' ) === 'inline-block', 'Shown' );
    } );

    test( 'textarea', function() {
        var input = new Ui.Input( { area: true } );
        $( 'body' ).prepend( input.$el );
        ok( input.tagName === 'textarea', 'Created textarea.' );
        ok( input.value() === undefined, 'Unavailable value.' );
        input.model.set( 'value', '_value' );
        ok( input.value() === '_value', 'Correct new value.' );
        ok( !input.$el.hasClass( '_cls' ), 'Has no custom class.' );
        input.model.set( 'cls', '_cls' );
        ok( input.$el.hasClass( '_cls' ), 'Has custom class.' );
    } );

    test( 'message', function() {
        var message = new Ui.Message({
            persistent  : true,
            message     : '_message',
            status      : 'danger'
        });
        $( 'body' ).prepend( message.$el );
        ok( message.$el.hasClass( 'alert-danger' ), 'Alert danger.' );
        message.model.set( 'status', 'info' );
        ok( !message.$el.hasClass( 'alert-danger' ), 'Alert danger (disabled).' );
        ok( message.$el.hasClass( 'alert-info' ), 'Alert info.' );
        ok( message.$el.html() === '_message', 'Correct message.' );
        message.model.set( 'message', '_new_message' );
        ok( message.$el.html() === '_new_message', 'Correct new message.' );
    } );

    test( 'hidden', function() {
        var hidden = new Ui.Hidden();
        $( 'body' ).prepend( hidden.$el );
        hidden.model.set( 'info', '_info' );
        ok( hidden.$info.css( 'display', 'block' ), 'Info shown.' );
        ok( hidden.$info.html() === '_info', 'Info text correct.' );
        hidden.model.set( 'info', '' );
        ok( hidden.$info.css( 'display', 'none' ), 'Info hidden.' );
        hidden.model.set( 'value', '_value' );
        ok( hidden.$hidden.val() === '_value', 'Correct value' );
    } );

    test( 'select-content', function() {
        var select = new SelectContent.View({});
        $( 'body' ).prepend( select.$el );
        ok ( select.button_type.value() == 0, 'Initial mode selected by default.' );
        select.model.set( 'data', { 'hda':  [{ id: 'id0', name: 'name0', hid: 'hid0' },
                                             { id: 'id1', name: 'name1', hid: 'hid1' }],
                                    'hdca': [{ id: 'id2', name: 'name2', hid: 'hid2' },
                                             { id: 'id3', name: 'name3', hid: 'hid3' },
                                             { id: 'id4', name: 'name4', hid: 'hid4' }] } );
        ok ( select.button_type.$( '.ui-option' ).length == 3, 'Found 3 radio button options' );
        ok ( select.button_type.$( '.ui-option:first' ).hasClass( 'active' ), 'First one is toggled' );
        ok ( select.$( '.ui-select' ).length == 3, 'Found 3 select fields' );
        ok ( select.$( '.ui-select:first' ).find( 'option' ).length == 2, 'First one has 2 options' );
        ok ( select.$( 'option:first' ).prop( 'value' ) == 'id0', 'First option has correct value' );
        ok ( select.$( 'option:first' ).text() == 'hid0: name0', 'First option has correct label' );
        ok ( select.$( '.ui-select-multiple' ).length == 1, 'Contains one multiselect field' );
        ok ( select.$( '.ui-select-multiple' ).find( 'option' ).length == 2, 'Multiselect has two options' );
        ok ( select.$( '.ui-select-multiple' ).find( 'option:first' ).prop( 'value' ) == 'id0', 'First option has correct value' );
        ok ( select.$( '.ui-select-multiple' ).find( 'option:first' ).text() == 'hid0: name0', 'First option has correct label' );
        ok ( select.$( '.ui-select:last' ).find( 'option' ).length == 3, 'Last one has 3 options' );
        ok ( select.$( '.ui-select:last' ).find( 'option:first' ).prop( 'value' ) == 'id2', 'First option has correct value' );
        ok ( select.$( '.ui-select:last' ).find( 'option:first' ).text() == 'hid2: name2', 'First option has correct label' );
        ok ( select.button_type.$el.css( 'display' ) == 'block', 'Radio button visible' );
        select.model.set( 'wait', true );
        ok ( select.$( '.icon-dropdown' ).hasClass( 'fa-spinner' ), 'Shows spinner' );
        select.model.set( 'wait', false );
        ok ( select.$( '.icon-dropdown' ).hasClass( 'fa-caret-down' ), 'Shows caret' );
        select.model.set( 'multiple', true );
        select.model.set( 'type', 'data' );
        ok ( select.button_type.$( '.ui-option' ).length == 2, 'Found 2 radio button options' );
        ok ( select.button_type.$( '.ui-option:first' ).hasClass( 'active' ), 'First one is toggled' );
        ok ( select.$( '.ui-select' ).length == 2, 'Found two select fields' );
        ok ( select.$( '.ui-select:first' ).find( 'option' ).length == 2, 'First one has 2 options' );
        ok ( select.$( 'option:first' ).prop( 'value' ) == 'id0', 'First option has correct value' );
        ok ( select.$( 'option:first' ).text() == 'hid0: name0', 'First option has correct label' );
        ok ( select.$( '.ui-select' ).hasClass( 'ui-select-multiple' ), 'First one allows multiple selections' );
        ok ( select.$( '.ui-select-multiple' ).length == 1, 'Contains one multiselect field' );
        ok ( select.$( '.ui-select:last' ).find( 'option' ).length == 3, 'Last one has 3 options' );
        ok ( select.$( '.ui-select:last' ).find( 'option:first' ).prop( 'value' ) == 'id2', 'First option has correct value' );
        ok ( select.$( '.ui-select:last' ).find( 'option:first' ).text() == 'hid2: name2', 'First option has correct label' );
        ok ( select.button_type.$el.css( 'display' ) == 'block', 'Radio button visible' );
        select.model.set( 'multiple', false );
        select.model.set( 'type', 'data_collection' );
        ok ( select.$( '.ui-select' ).length == 1, 'Found one select fields' );
        ok ( select.$( '.ui-select:first' ).find( 'option' ).length == 3, 'First one has 3 options' );
        ok ( select.$( 'option:first' ).prop( 'value' ) == 'id2', 'First option has correct value' );
        ok ( select.$( 'option:first' ).text() == 'hid2: name2', 'First option has correct label' );
        ok ( !select.$( '.ui-select' ).hasClass( 'ui-select-multiple' ), 'First does not allow multiple selections' );
        ok ( select.$( '.ui-select-multiple' ).length == 0, 'Does not contain any multiselect field' );
        ok ( select.button_type.$el.css( 'display' ) == '', 'Radio button not visible' );
        select.model.set( 'type', 'data' );
        ok ( select.button_type.$el.css( 'display' ) == 'block', 'Radio button visible, again' );
        select.model.set( 'value', { values: [ { id: 'id1', src: 'hda' } ] } );
        ok( JSON.stringify( select.value() ) == '{"batch":false,"values":[{"id":"id1","name":"name1","hid":"hid1"}]}', 'Checking single value' );
        ok( select.config[ select.model.get( 'current' ) ].src == 'hda', 'Matched dataset field' );
        ok( !select.config[ select.model.get( 'current' ) ].multiple, 'Matched single select field' );
        select.model.set( 'value', { values: [ { id: 'id0', src: 'hda' }, { id: 'id1', src: 'hda' } ] } );
        ok( select.config[ select.model.get( 'current' ) ].multiple, 'Matched multiple field' );
        ok( JSON.stringify( select.value() ) == '{"batch":true,"values":[{"id":"id0","name":"name0","hid":"hid0"},{"id":"id1","name":"name1","hid":"hid1"}]}', 'Checking multiple values' );
        select.model.set( 'value', { values: [ { id: 'id2', src: 'hdca' } ] } );
        ok( select.config[ select.model.get( 'current' ) ].src == 'hdca', 'Matched collection field' );
        ok( JSON.stringify( select.value() ) == '{"batch":true,"values":[{"id":"id2","name":"name2","hid":"hid2"}]}', 'Checking collection value' );
    } );
});