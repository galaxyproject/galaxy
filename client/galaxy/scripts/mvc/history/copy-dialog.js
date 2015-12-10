define([
    "utils/localization"
], function( _l ){
    "use strict";
/* =============================================================================
Wrapper function around the global Galaxy.modal for use when copying histories.

TODO:
    need:
        copy that allows:
            all datasets
            non-deleted datasets
            ?choose datasets
        import that allows:
            all datasets
            non-deleted datasets
        import that's only:
            non-deleted datasets

    language changes only between copy/import

    import : defaults to false
    allowAll : defaults to true

==============================================================================*/
// maintain the (slight) distinction between copy and import

// /** show the dialog and handle validation, ajax, and callbacks */
// function historyCopyDialog( history, options ){
//     options = options || {};

//     // fall back to un-notifying copy
//     if( !( Galaxy && Galaxy.modal ) ){
//         return history.copy();
//     }

//     var modal = Galaxy.modal,
//         deferred = jQuery.Deferred(),
//         historyName = _.escape( history.get( 'name' ) ),
//         defaultCopyName = "Copy of '" + historyName + "'",
//         defaultCopyWhat = options.allDatasets? 'copy-all' : 'copy-non-deleted',
//         allowAll = !_.isUndefined( options.allowAll )? options.allowAll : true;

//     // validate the name and copy if good
//     function checkNameAndCopy(){
//         var name = modal.$( '#copy-modal-title' ).val();
//         if( !name ){
//             modal.$( '.invalid-title' ).show();
//             return;
//         }
//         // get further settings, shut down and indicate the ajax call, then hide and resolve/reject
//         var copyAllDatasets = modal.$( 'input[name="copy-what"]:checked' ).val() === 'copy-all';
//         modal.$( 'button' ).prop( 'disabled', true );
//         showAjaxIndicator();
//         history.copy( true, name, copyAllDatasets )
//             .done( function( response ){
//                 deferred.resolve( response );
//             })
//             //TODO: make this unneccessary with pub-sub error or handling via Galaxy
//             .fail( function(){
//                 alert( _l( 'History could not be copied. Please contact a Galaxy administrator' ) );
//                 deferred.rejectWith( deferred, arguments );
//             })
//             .always( function(){
//                 modal.hide();
//             });
//     }

//     var originalClosingCallback = options.closing_callback;
//     modal.show( _.extend( options, {
//         title   : _l( 'Copying history' ) + ' "' + historyName + '"',
//         body    : $( templateDialog({
//                 name    : defaultCopyName,
//                 isAnon  : Galaxy.user.isAnonymous(),
//                 allowAll: allowAll,
//                 copyWhat: defaultCopyWhat
//             })),
//         buttons : _.object([
//                 [ _l( 'Cancel' ),   function(){ modal.hide(); } ],
//                 [ _l( 'Copy' ),     checkNameAndCopy ]
//             ]),
//         height          : 'auto',
//         closing_events  : true,
//         closing_callback: function _historyCopyClose( cancelled ){
//                 if( cancelled ){
//                     deferred.reject({ cancelled : true });
//                 }
//                 if( originalClosingCallback ){
//                     originalClosingCallback( cancelled );
//                 }
//             }
//         }));

//     // set the default dataset copy, autofocus the title, and set up for a simple return
//     modal.$( '#copy-modal-title' ).focus().select();
//     modal.$( '#copy-modal-title' ).on( 'keydown', function( ev ){
//         if( ev.keyCode === 13 ){
//             ev.preventDefault();
//             checkNameAndCopy();
//         }
//     });

//     return deferred;
// }


//==============================================================================
var CopyDialog = {

    defaultName     : _.template( "Copy of '<%- name %>'" ),
    title           : _.template( _l( 'Copying history' ) + ' "<%- name %>"' ),
    submitLabel     : _l( 'Copy' ),
    errorMessage    : _l( 'History could not be copied' ),
    progressive     : _l( 'Copying history' ),
    activeLabel     : _l( 'Copy only the active, non-deleted datasets' ),
    allLabel        : _l( 'Copy all datasets including deleted ones' ),
    anonWarning     : _l( 'As an anonymous user, unless you login or register, you will lose your current history ' ) +
                      _l( 'after copying this history. ' ),

    template : _.template([
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

    showAjaxIndicator : function _showAjaxIndicator(){
        var indicator = '<p><span class="fa fa-spinner fa-spin"></span> ' + this.progressive + '...</p>';
        this.modal.$( '.modal-body' ).empty().append( indicator ).css({ 'margin-top': '8px' });
    },

    dialog : function _dialog( modal, history, options ){
        options = options || {};
        // fall back to un-notifying copy
        if( !modal ){
            return history.copy();
        }
        this.modal = modal;

        var dialog = this,
            deferred = jQuery.Deferred(),
            defaultCopyName = this.defaultName({ name: history.get( 'name' ) }),
            defaultCopyWhat = options.allDatasets? 'copy-all' : 'copy-non-deleted',
            allowAll = !_.isUndefined( options.allowAll )? options.allowAll : true;

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
            dialog.showAjaxIndicator();
            history.copy( true, name, copyAllDatasets )
                .done( function( response ){
                    deferred.resolve( response );
                })
                //TODO: make this unneccessary with pub-sub error or handling via Galaxy
                .fail( function(){
                    alert([ this.errorMessage, _l( 'Please contact a Galaxy administrator' ) ].join( '. ' ));
                    deferred.rejectWith( deferred, arguments );
                })
                .always( function(){
                    modal.hide();
                });
        }

        var originalClosingCallback = options.closing_callback;
        modal.show( _.extend( options, {
            title   : this.title({ name: history.get( 'name' ) }),
            body    : $( dialog.template({
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
var ImportDialog = _.extend( {}, CopyDialog, {
    defaultName     : _.template( "imported: '<%- name %>" ),
    title           : _.template( _l( 'Importing history' ) + ' "<%- name %>"' ),
    submitLabel     : _l( 'Import' ),
    errorMessage    : _l( 'History could not be imported' ),
    progressive     : _l( 'Importing history' ),
    activeLabel     : _l( 'Import only the active, non-deleted datasets' ),
    allLabel        : _l( 'Import all datasets including deleted ones' ),
    anonWarning     : _l( 'As an anonymous user, unless you login or register, you will lose your current history ' ) +
                      _l( 'after importing this history. ' ),

});

//==============================================================================
var historyCopyDialog = function( history, options ){
    options = options || {};
    return options.import?
        ImportDialog.dialog( Galaxy.modal, history, options ):
        CopyDialog.dialog( Galaxy.modal, history, options );
};


//==============================================================================
    return historyCopyDialog;
});
