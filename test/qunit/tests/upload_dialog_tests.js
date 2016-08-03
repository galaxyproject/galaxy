/* global define, QUnit, module, test, ok, equal, deepEqual, notEqual */
define([ "test-app", "mvc/upload/upload-view"
], function( testApp, GalaxyUpload ){
    "use strict";
    module( "Upload dialog test", {
        setup: function( ) {
            testApp.create();
            this.app = new GalaxyUpload();
        },
        teardown: function() {
            testApp.destroy();
        }
    } );

    test( "test initial dialog state", function() {
        $(this.app.ui_button.$el).trigger('click');
        ok(this.app.default_view.collection.length == 0, 'Invalid initial upload item collection.');
        ok($('#btn-start').hasClass('disabled'), 'Start button should be disabled.');
        ok($('#btn-stop').hasClass('disabled'), 'Stop button should be disabled.');
        ok($('#btn-reset').hasClass('disabled'), 'Reset button should be disabled.');
    } );

    test( "test adding/removing paste/fetch upload item", function() {
        $(this.app.ui_button.$el).trigger('click');
        $('#btn-new').trigger('click');
        ok(!$('#btn-start').hasClass('disabled'), 'Start button should be enabled.');
        ok($('#btn-stop').hasClass('disabled'), 'Stop button should (still) be disabled.');
        ok(!$('#btn-reset').hasClass('disabled'), 'Reset button should be enabled.');
        ok(this.app.default_view.collection.length == 1, 'Invalid upload item collection length after adding item.');
        ok($('#btn-new').find('i').hasClass('fa-edit'), 'Paste/fetch icon changed');
        ok($('#btn-start').hasClass('btn-primary'), 'Start button should be enabled/highlighted.');
        ok($('#upload-row-0').find('.upload-symbol').hasClass('fa-trash-o'), 'Should show regular trash icon.');
        $('#upload-row-0').find('.upload-settings').trigger('click');
        ok($('#upload-row-0').find('.upload-settings-cover').css('display') == 'none', 'Settings should be enabled.');
        $('#upload-row-0').find('.popover-close').trigger('click');
        $('#btn-start').trigger('click');
        ok($('#upload-row-0').find('.upload-symbol').hasClass('fa-exclamation-triangle'), 'Upload attempt should have failed.');
        ok($('#upload-row-0').find('.upload-settings').trigger('click'));
        ok($('#upload-row-0').find('.upload-settings-cover').css('display') == 'block', 'Settings should be disabled.');
        $('#upload-row-0').find('.upload-symbol').trigger('click');
        ok(this.app.default_view.collection.length == 0, 'Removing item from collection failed.');
    } );

    test( "test ftp popup", function() {
        $(this.app.ui_button.$el).trigger('click');
        $('#btn-ftp').trigger('click');
        ok($('.upload-ftp-help').length == 1, 'Should show ftp help text.');
    } );
});