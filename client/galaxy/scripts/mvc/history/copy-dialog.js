define([
    "mvc/ui/ui-modal",
    "mvc/ui/error-modal",
    "utils/localization"
], function( MODAL, ERROR_MODAL, _l ){

'use strict';

//==============================================================================
/**
 * A dialog/modal that allows copying a user history or 'importing' from user
 * another. Generally called via historyCopyDialog below.
 * @type {Object}
 */
var CopyDialog = {

    // language related strings/fns
    defaultName     : _.template( "Copy of '<%- name %>'" ),
    title           : _.template( _l( 'Copying history' ) + ' "<%- name %>"' ),
    submitLabel     : _l( 'Copy' ),
    errorMessage    : _l( 'History could not be copied.' ),
    progressive     : _l( 'Copying history' ),
    activeLabel     : _l( 'Copy only the active, non-deleted datasets' ),
    allLabel        : _l( 'Copy all datasets including deleted ones' ),
    anonWarning     : _l( 'As an anonymous user, unless you login or register, you will lose your current history ' ) +
                      _l( 'after copying this history. ' ),

    // template for modal body
    _template : _.template([
        //TODO: remove inline styles
        // show a warning message for losing current to anon users
        '<% if( isAnon ){ %>',
            '<div class="warningmessage">',
                '<%- anonWarning %>',
                _l( 'You can' ),
                ' <a href="/user/login">', _l( 'login here' ), '</a> ', _l( 'or' ), ' ',
                ' <a href="/user/create">', _l( 'register here' ), '</a>.',
            '</div>',
        '<% } %>',
        '<form>',
            '<label for="copy-modal-title">',
                _l( 'Enter a title for the new history' ), ':',
            '</label><br />',
            // TODO: could use required here and the form validators
            // NOTE: use unescaped here if escaped in the modal function below
            '<input id="copy-modal-title" class="form-control" style="width: 100%" value="<%= name %>" />',
            '<p class="invalid-title bg-danger" style="color: red; margin: 8px 0px 8px 0px; display: none">',
                _l( 'Please enter a valid history title' ),
            '</p>',
            // if allowAll, add the option to copy deleted datasets, too
            '<% if( allowAll ){ %>',
                '<br />',
                '<p>', _l( 'Choose which datasets from the original history to include:' ), '</p>',
                // copy non-deleted is the default
                '<input name="copy-what" type="radio" id="copy-non-deleted" value="copy-non-deleted" ',
                    '<% if( copyWhat === "copy-non-deleted" ){ print( "checked" ); } %>/>',
                '<label for="copy-non-deleted"> <%- activeLabel %></label>',
                '<br />',
                '<input name="copy-what" type="radio" id="copy-all" value="copy-all" ',
                    '<% if( copyWhat === "copy-all" ){ print( "checked" ); } %>/>',
                '<label for="copy-all"> <%- allLabel %></label>',
            '<% } %>',
        '</form>'
    ].join( '' )),

    // empty modal body and let the user know the copy is happening
    _showAjaxIndicator : function _showAjaxIndicator(){
        var indicator = '<p><span class="fa fa-spinner fa-spin"></span> ' + this.progressive + '...</p>';
        this.modal.$( '.modal-body' ).empty().append( indicator ).css({ 'margin-top': '8px' });
    },

    // (sorta) public interface - display the modal, render the form, and potentially copy the history
    // returns a jQuery.Deferred done->history copied, fail->user cancelled
    dialog : function _dialog( modal, history, options ){
        options = options || {};

        var dialog = this,
            deferred = jQuery.Deferred(),
            // TODO: getting a little byzantine here
            defaultCopyNameFn = options.nameFn || this.defaultName,
            defaultCopyName = defaultCopyNameFn({ name: history.get( 'name' ) }),
            // TODO: these two might be simpler as one 3 state option (all,active,no-choice)
            defaultCopyWhat = options.allDatasets? 'copy-all' : 'copy-non-deleted',
            allowAll = !_.isUndefined( options.allowAll )? options.allowAll : true,
            autoClose = !_.isUndefined( options.autoClose )? options.autoClose : true;

        this.modal = modal;


        // validate the name and copy if good
        function checkNameAndCopy(){
            var name = modal.$( '#copy-modal-title' ).val();
            if( !name ){
                modal.$( '.invalid-title' ).show();
                return;
            }
            // get further settings, shut down and indicate the ajax call, then hide and resolve/reject
            var copyAllDatasets = modal.$( 'input[name="copy-what"]:checked' ).val() === 'copy-all';
            modal.$( 'button' ).prop( 'disabled', true );
            dialog._showAjaxIndicator();
            history.copy( true, name, copyAllDatasets )
                .done( function( response ){
                    deferred.resolve( response );
                })
                .fail( function( xhr, status, message ){
                    var options = { name: name, copyAllDatasets: copyAllDatasets };
                    ERROR_MODAL.ajaxErrorModal( history, xhr, options, dialog.errorMessage );
                    deferred.rejectWith( deferred, arguments );
                })
                .done( function(){
                    if( autoClose ){ modal.hide(); }
                });
        }

        var originalClosingCallback = options.closing_callback;
        modal.show( _.extend( options, {
            title   : this.title({ name: history.get( 'name' ) }),
            body    : $( dialog._template({
                    name        : defaultCopyName,
                    isAnon      : Galaxy.user.isAnonymous(),
                    allowAll    : allowAll,
                    copyWhat    : defaultCopyWhat,
                    activeLabel : this.activeLabel,
                    allLabel    : this.allLabel,
                    anonWarning : this.anonWarning,
                })),
            buttons : _.object([
                    [ _l( 'Cancel' ),   function(){ modal.hide(); } ],
                    [ this.submitLabel, checkNameAndCopy ]
                ]),
            height          : 'auto',
            closing_events  : true,
            closing_callback: function _historyCopyClose( cancelled ){
                    if( cancelled ){
                        deferred.reject({ cancelled : true });
                    }
                    if( originalClosingCallback ){
                        originalClosingCallback( cancelled );
                    }
                }
            }));

        // set the default dataset copy, autofocus the title, and set up for a simple return
        modal.$( '#copy-modal-title' ).focus().select();
        modal.$( '#copy-modal-title' ).on( 'keydown', function( ev ){
            if( ev.keyCode === 13 ){
                ev.preventDefault();
                checkNameAndCopy();
            }
        });

        return deferred;
    },
};

//==============================================================================
// maintain the (slight) distinction between copy and import
/**
 * Subclass CopyDialog to use the import language.
 */
var ImportDialog = _.extend( {}, CopyDialog, {
    defaultName     : _.template( "imported: <%- name %>" ),
    title           : _.template( _l( 'Importing history' ) + ' "<%- name %>"' ),
    submitLabel     : _l( 'Import' ),
    errorMessage    : _l( 'History could not be imported.' ),
    progressive     : _l( 'Importing history' ),
    activeLabel     : _l( 'Import only the active, non-deleted datasets' ),
    allLabel        : _l( 'Import all datasets including deleted ones' ),
    anonWarning     : _l( 'As an anonymous user, unless you login or register, you will lose your current history ' ) +
                      _l( 'after importing this history. ' ),

});

//==============================================================================
/**
 * Main interface for both history import and history copy dialogs.
 * @param  {Backbone.Model} history     the history to copy
 * @param  {Object}         options     a hash
 * @return {jQuery.Deferred}            promise that fails on close and succeeds on copy
 *
 * options:
 *     (this object is also passed to the modal used to display the dialog and accepts modal options)
 *     {Function} nameFn    if defined, use this to build the default name shown to the user
 *                          (the fn is passed: {name: <original history's name>})
 *     {bool} useImport     if true, use the 'import' language (instead of Copy)
 *     {bool} allowAll      if true, allow the user to choose between copying all datasets and
 *                          only non-deleted datasets
 *     {String} allDatasets default initial checked radio button: 'copy-all' or 'copy-non-deleted',
 */
var historyCopyDialog = function( history, options ){
    options = options || {};
    // create our own modal if Galaxy doesn't have one (mako tab without use_panels)
    var modal = window.parent.Galaxy.modal || new MODAL.View({});
    return options.useImport?
        ImportDialog.dialog( modal, history, options ):
        CopyDialog.dialog( modal, history, options );
};


//==============================================================================
    return historyCopyDialog;
});
