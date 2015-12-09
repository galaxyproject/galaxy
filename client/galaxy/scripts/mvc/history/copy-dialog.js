define([
    "utils/localization"
], function( _l ){
/* =============================================================================
Wrapper function around the global Galaxy.modal for use when copying histories.

==============================================================================*/
function _renderBody( vars ){
    var body = [
        '<form>',
            '<label for="copy-modal-title">',
                _l( 'Enter a title for the copied history' ), ':',
            '</label><br />',
            '<input id="copy-modal-title" class="form-control" style="width: 100%" ',
                // TODO: could use required here and the form validators
                'value="', vars.defaultCopyName, '" />',
            '<br />',
            '<p>', _l( 'Choose which datasets from the original history to include:' ), '</p>',
            // copy non-deleted is the default
            '<input name="copy-what" type="radio" id="copy-non-deleted" value="copy-non-deleted" />',
            '<label for="copy-non-deleted"> ',
                _l( 'Copy only the active (non-deleted) datasets' ),
            '</label><br />',
            '<input name="copy-what" type="radio" id="copy-all" value="copy-all" />',
            '<label for="copy-all"> ',
                _l( 'Copy all datasets including deleted ones' ),
            '</label><br />',
        '</form>'
    ].join('');
    return vars.isAnon? ( _renderAnonWarning() + body ): body;
}

function _renderAnonWarning(){
    return [
        '<div class="warningmessage">',
            _l( 'As an anonymous user, unless you login or register, you will lose your current history ' ),
            _l( 'after making a copy of this history. ' ),
            _l( 'You can' ),
            ' <a href="/user/login">', _l( 'login here' ), '</a> ', _l( 'or' ), ' ',
            ' <a href="/user/create">', _l( 'register here' ), '</a>.',
        '</div>'
    ].join( '' );
}

function _validateName( name ){
    if( !name ){
        if( !Galaxy.modal.$( '#invalid-title' ).size() ){
            var $invalidTitle = $( '<p/>' ).attr( 'id', 'invalid-title' )
                .css({ color: 'red', 'margin': '8px 0px 8px 0px' })
                .addClass( 'bg-danger' )
                .text( _l( 'Please enter a valid history title' ) )
                .insertAfter( Galaxy.modal.$( '#copy-modal-title' ) );
        }
        return false;
    }
    return name;
}

function _renderCopyIndicator(){
    return $([
            '<p>', '<span class="fa fa-spinner fa-spin"></span> ', _l( 'Copying history' ), '...', '</p>'
        ].join( '' ))
        //TODO: move out of inline
        .css({ 'margin-top': '8px' });
}

/** show the dialog and handle validation, ajax, and callbacks */
function historyCopyDialog( history, options ){
    options = options || {};

    // fall back to un-notifying copy
    if( !( Galaxy && Galaxy.modal ) ){
        return history.copy();
    }

    var deferred = jQuery.Deferred(),
        historyName = _.escape( history.get( 'name' ) ),
        defaultCopyName = options.name || ( "Copy of '" + historyName + "'" ),
        defaultCopyWhat = options.allDatasets? 'copy-all' : 'copy-non-deleted';

    // do the actual work of copying here
    function copyHistory( name ){
        var copyAllDatasets = Galaxy.modal.$( 'input[name="copy-what"]:checked' ).val() === 'copy-all',
            $copyIndicator = _renderCopyIndicator();
        Galaxy.modal.$( '.modal-body' ).empty().append( $copyIndicator );
        Galaxy.modal.$( 'button' ).prop( 'disabled', true );
        history.copy( true, name, copyAllDatasets )
            .done( function( response ){
                deferred.resolve( response );
            })
            //TODO: make this unneccessary with pub-sub error or handling via Galaxy
            .fail( function(){
                alert( _l( 'History could not be copied. Please contact a Galaxy administrator' ) );
                deferred.rejectWith( deferred, arguments );
            })
            .always( function(){
                Galaxy.modal.hide();
            });
    }

    // validate the name and copy if good
    function checkNameAndCopy(){
        var name = Galaxy.modal.$( '#copy-modal-title' ).val();
        if( !_validateName( name ) ){ return; }
        copyHistory( name );
    }

    var originalClosingCallback = options.closing_callback;
    options.height = 'auto';
    options.closing_callback = function _historyCopyClose( cancelled ){
        if( cancelled ){
            deferred.reject({ cancelled : true });
        }
        if( originalClosingCallback ){
            originalClosingCallback( cancelled );
        }
    };
    Galaxy.modal.show( _.extend({
        title   : _l( 'Copying history' ) + ' "' + historyName + '"',
        body    : $( _renderBody({
            defaultCopyName : defaultCopyName,
            isAnon          : Galaxy.user.isAnonymous()
        })),
        buttons : {
            'Cancel' : function(){ Galaxy.modal.hide(); },
            'Copy'   : checkNameAndCopy
        },
        closing_events : true
    }, options ));

    $( '#' + defaultCopyWhat ).prop( 'checked', true );

    $( '#copy-modal-title' ).focus().select();
    $( '#copy-modal-title' ).on( 'keydown', function( ev ){
        if( ev.keyCode === 13 ){
            ev.preventDefault();
            checkNameAndCopy();
        }
    });

    return deferred;
}

//==============================================================================
    return historyCopyDialog;
});
