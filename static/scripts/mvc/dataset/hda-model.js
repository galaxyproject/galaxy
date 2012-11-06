//define([
//    "../mvc/base-mvc"
//], function(){
//==============================================================================
/**
 *
 */
var HistoryDatasetAssociation = BaseModel.extend( LoggableMixin ).extend({
    // a single HDA model
    
    // uncomment this out see log messages
    //logger              : console,
    
    defaults : {
        // ---these are part of an HDA proper:

        // parent (containing) history
        history_id          : null,
        // often used with tagging
        model_class         : 'HistoryDatasetAssociation',
        // index within history (??)
        hid                 : 0,
        
        // ---whereas these are Dataset related/inherited

        id                  : null, 
        name                : '',
        // one of HistoryDatasetAssociation.STATES
        state               : '',
        // sniffed datatype (sam, tabular, bed, etc.)
        data_type           : null,
        // size in bytes
        file_size           : 0,

        // array of associated file types (eg. [ 'bam_index', ... ])
        meta_files          : [],

        misc_blurb          : '', 
        misc_info           : '',

        deleted             : false, 
        purged              : false,
        // aka. !hidden
        visible             : false,
        // based on trans.user (is_admin or security_agent.can_access_dataset( <user_roles>, hda.dataset ))
        accessible          : false,
        
        //TODO: this needs to be removed (it is a function of the view type (e.g. HDAForEditingView))
        for_editing         : true
    },

    // fetch location of this history in the api
    url : function(){
        //TODO: get this via url router
        return 'api/histories/' + this.get( 'history_id' ) + '/contents/' + this.get( 'id' );
    },
    
    // (curr) only handles changing state of non-accessible hdas to STATES.NOT_VIEWABLE
    //TODO:? use initialize (or validate) to check purged AND deleted -> purged XOR deleted
    initialize : function(){
        this.log( this + '.initialize', this.attributes );
        this.log( '\tparent history_id: ' + this.get( 'history_id' ) );
        
        //!! this state is not in trans.app.model.Dataset.states - set it here -
        //TODO: change to server side.
        if( !this.get( 'accessible' ) ){
            this.set( 'state', HistoryDatasetAssociation.STATES.NOT_VIEWABLE );
        }

        // if the state has changed and the new state is a ready state, fire an event
        this.on( 'change:state', function( currModel, newState ){
            this.log( this + ' has changed state:', currModel, newState );
            if( this.inReadyState() ){
                this.trigger( 'state:ready', this.get( 'id' ), newState, this.previous( 'state' ), currModel );
            }
        });

        // debug on change events
        //this.on( 'change', function( currModel, changedList ){
        //    this.log( this + ' has changed:', currModel, changedList );
        //});
        //this.bind( 'all', function( event ){
        //    this.log( this + '', arguments );
        //});
    },

    isDeletedOrPurged : function(){
        return ( this.get( 'deleted' ) || this.get( 'purged' ) );
    },

    // based on show_deleted, show_hidden (gen. from the container control), would this ds show in the list of ds's?
    //TODO: too many visibles
    isVisible : function( show_deleted, show_hidden ){
        var isVisible = true;
        if( ( !show_deleted )
        &&  ( this.get( 'deleted' ) || this.get( 'purged' ) ) ){
            isVisible = false;
        }
        if( ( !show_hidden )
        &&  ( !this.get( 'visible' ) ) ){
            isVisible = false;
        }
        return isVisible;
    },
    
    // 'ready' states are states where no processing (for the ds) is left to do on the server
    inReadyState : function(){
        var state = this.get( 'state' );
        return (
            ( state === HistoryDatasetAssociation.STATES.NEW )
        ||  ( state === HistoryDatasetAssociation.STATES.OK )
        ||  ( state === HistoryDatasetAssociation.STATES.EMPTY )
        ||  ( state === HistoryDatasetAssociation.STATES.FAILED_METADATA )
        ||  ( state === HistoryDatasetAssociation.STATES.NOT_VIEWABLE )
        ||  ( state === HistoryDatasetAssociation.STATES.DISCARDED )
        ||  ( state === HistoryDatasetAssociation.STATES.ERROR )
        );
    },

    // convenience fn to match hda.has_data
    hasData : function(){
        //TODO:?? is this equivalent to all possible hda.has_data calls?
        return ( this.get( 'file_size' ) > 0 );
    },

    toString : function(){
        var nameAndId = this.get( 'id' ) || '';
        if( this.get( 'name' ) ){
            nameAndId += ':"' + this.get( 'name' ) + '"';
        }
        return 'HistoryDatasetAssociation(' + nameAndId + ')';
    }
});

//------------------------------------------------------------------------------
HistoryDatasetAssociation.STATES = {
    UPLOAD              : 'upload',
    QUEUED              : 'queued',
    RUNNING             : 'running',
    SETTING_METADATA    : 'setting_metadata',

    NEW                 : 'new',
    OK                  : 'ok',
    EMPTY               : 'empty',

    FAILED_METADATA     : 'failed_metadata',
    NOT_VIEWABLE        : 'noPermission',   // not in trans.app.model.Dataset.states
    DISCARDED           : 'discarded',
    ERROR               : 'error'
};

//==============================================================================
/**
 *
 */
var HDACollection = Backbone.Collection.extend( LoggableMixin ).extend({
    model           : HistoryDatasetAssociation,

    //logger          : console,

    initialize : function(){
        //this.bind( 'all', function( event ){
        //    this.log( this + '', arguments );
        //});
    },

    // return the ids of every hda in this collection
    ids : function(){
        return this.map( function( item ){ return item.id; });
    },

    // return an HDA collection containing every 'shown' hda based on show_deleted/hidden
    getVisible : function( show_deleted, show_hidden ){
        return this.filter( function( item ){ return item.isVisible( show_deleted, show_hidden ); });
    },

    // get a map where <possible hda state> : [ <list of hda ids in that state> ]
    getStateLists : function(){
        var stateLists = {};
        _.each( _.values( HistoryDatasetAssociation.STATES ), function( state ){
            stateLists[ state ] = [];
        });
        //NOTE: will err on unknown state
        this.each( function( item ){
            stateLists[ item.get( 'state' ) ].push( item.get( 'id' ) );
        });
        return stateLists;
    },

    // returns the id of every hda still running (not in a ready state)
    running : function(){
        var idList = [];
        this.each( function( item ){
            if( !item.inReadyState() ){
                idList.push( item.get( 'id' ) );
            }
        });
        return idList;
    },

    // update (fetch -> render) the hdas with the ids given
    update : function( ids ){
        this.log( this + 'update:', ids );

        if( !( ids && ids.length ) ){ return; }

        var collection = this;
        _.each( ids, function( id, index ){
            var historyItem = collection.get( id );
            historyItem.fetch();
        });
    },

    toString : function(){
         return ( 'HDACollection(' + this.ids().join(',') + ')' );
    }
});

//==============================================================================
//return {
//    HistoryDatasetAssociation : HistoryDatasetAssociation,
//    HDACollection             : HDACollection,
//};});
