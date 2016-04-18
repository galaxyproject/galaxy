define([
    "mvc/base-mvc"
], function( BASE_MVC ){

'use strict';

var logNamespace = 'history';

// ============================================================================
/** session storage for individual history preferences */
var HistoryPrefs = BASE_MVC.SessionStorageModel.extend(
/** @lends HistoryPrefs.prototype */{
    //TODO:?? move to user prefs?
    defaults : {
        //TODO:?? expandedIds to array?
        expandedIds : {},
        show_deleted : false,
        show_hidden  : false
    },

    /** add an hda id to the hash of expanded hdas */
    addExpanded : function( model ){
        var key = 'expandedIds';
        this.save( key, _.extend( this.get( key ), _.object([ model.id ], [ model.get( 'id' ) ]) ) );
    },

    /** remove an hda id from the hash of expanded hdas */
    removeExpanded : function( model ){
        var key = 'expandedIds';
        this.save( key, _.omit( this.get( key ), model.id ) );
    },

    toString : function(){
        return 'HistoryPrefs(' + this.id + ')';
    }

}, {
    // ........................................................................ class vars
    // class lvl for access w/o instantiation
    storageKeyPrefix : 'history:',

    /** key string to store each histories settings under */
    historyStorageKey : function historyStorageKey( historyId ){
        if( !historyId ){
            throw new Error( 'HistoryPrefs.historyStorageKey needs valid id: ' + historyId );
        }
        // single point of change
        return ( HistoryPrefs.storageKeyPrefix + historyId );
    },

    /** return the existing storage for the history with the given id (or create one if it doesn't exist) */
    get : function get( historyId ){
        return new HistoryPrefs({ id: HistoryPrefs.historyStorageKey( historyId ) });
    },

    /** clear all history related items in sessionStorage */
    clearAll : function clearAll( historyId ){
        for( var key in sessionStorage ){
            if( key.indexOf( HistoryPrefs.storageKeyPrefix ) === 0 ){
                sessionStorage.removeItem( key );
            }
        }
    }
});

//==============================================================================
    return {
        HistoryPrefs: HistoryPrefs
    };
});
