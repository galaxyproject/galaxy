define([
    "mvc/history/history-model",
    "mvc/history/history-panel-edit",
    "mvc/base-mvc",
    "utils/ajax-queue",
    "ui/mode-button",
    "ui/search-input"
], function( HISTORY_MODEL, HPANEL_EDIT, baseMVC, ajaxQueue ){
//==============================================================================
function _renderBody( vars ){
    return [
        '<form action="">',
            '<label for="copy-modal-title">',
                _l( 'Enter a title for the copied history' ), ':',
            '</label><br />',
            '<input id="copy-modal-title" class="form-control" style="width: 100%" value="', vars.defaultCopyName, '" />',
            '<br />',
            '<p>', _l( 'You can make a copy of the history that includes all datasets in the original history' ),
                   _l( ' or just the active (not deleted) datasets.' ), '</p>',
            // copy non-deleted is the default
            '<input name="copy-what" type="radio" id="copy-non-deleted" value="copy-non-deleted" checked />',
            '<label for="copy-non-deleted">', _l( 'Copy only active (not deleted) datasets' ), '</label><br />',
            '<input name="copy-what" type="radio" id="copy-all" value="copy-all" />',
            '<label for="copy-all">', _l( 'Copy all datasets, including deleted ones' ), '</label><br />',
        '</form>'
    ].join('');
}

function _validateName( name ){
    if( !name ){
        if( !Galaxy.modal.$( '#invalid-title' ).size() ){
            var $invalidTitle = $( '<p/>' ).attr( 'id', 'invalid-title' )
                .css({ color: 'red', 'margin-top': '8px' })
                .addClass( 'bg-danger' ).text( _l( 'Please enter a valid history title' ) );
            Galaxy.modal.$( '.modal-body' ).append( $invalidTitle );
        }
        return false;
    }
    return name;
}

/**  */
function historyCopyDialog( history, options ){
    options = options || {};
    // fall back to un-notifying copy
    if( !( Galaxy && Galaxy.modal ) ){
        return history.copy();
    }

    // maybe better as multiselect dialog?
    var historyName = history.get( 'name' ),
        defaultCopyName = "Copy of '" + historyName + "'";

    function copyHistory( name ){
        var copyAllDatasets = Galaxy.modal.$( 'input[name="copy-what"]:checked' ).val() === 'copy-all',
            $copyIndicator = $( '<p><span class="fa fa-spinner fa-spin"></span> Copying history...</p>' )
                .css({ 'margin-top': '8px' });
        Galaxy.modal.$( '.modal-body' ).children().replaceWith( $copyIndicator );
        Galaxy.modal.$( 'button' ).prop( 'disabled', true );
        history.copy( true, name, 'blah' )
            //TODO: make this unneccessary with pub-sub error
            .fail( function(){
                alert( _l( 'History could not be copied. Please contact a Galaxy administrator' ) );
            })
            .always( function(){
                Galaxy.modal.hide();
            });
    }
    function checkNameAndCopy(){
        var name = Galaxy.modal.$( '#copy-modal-title' ).val();
        if( !_validateName( name ) ){ return; }
        copyHistory( name );
    }

    Galaxy.modal.show( _.extend({
        title   : _l( 'Copying history' ) + ' "' + historyName + '"',
        body    : $( _renderBody({ defaultCopyName: defaultCopyName }) ),
        buttons : {
            'Cancel' : function(){ Galaxy.modal.hide(); },
            'Copy'   : checkNameAndCopy
        },
        closing_events : true
    }, options ));
    $( '#copy-modal-title' ).focus().select();
    $( '#copy-modal-title' ).on( 'keydown', function( ev ){
        if( ev.keyCode === 13 ){
            checkNameAndCopy();
        }
    });
}

//==============================================================================
    return historyCopyDialog;
});
