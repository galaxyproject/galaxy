define([
    "utils/localization"
], function( _l ){

    function _errorModal( message, title ){
        Galaxy.modal.show({
            title   : _l( title ),
            body    : _l( message ),
            buttons : { 'Ok': function(){ Galaxy.modal.hide(); } },
            closing_events: true
        });
    }

    function _errorAlert( message, title ){
        alert( title + '\n\n' + message );
    }

    function errorModal( message, title ){
        if( !message ){ return; }
        title = title || 'Error';
        if( window.Galaxy && Galaxy.modal ){
            return _errorModal( message, title );
        }
        return _errorAlert( message, title );
    }


return errorModal;
});
