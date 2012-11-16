//define([
//    "../mvc/base-mvc"
//], function(){
//==============================================================================
/** @class (HDA) model for a Galaxy dataset
 *      related to a history.
 *  @name HistoryDatasetAssociation
 *
 *  @augments BaseModel
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HistoryDatasetAssociation = BaseModel.extend( LoggableMixin ).extend(
/** @lends HistoryDatasetAssociation.prototype */{
    
    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,
    
    /** default attributes for a model */
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
        accessible          : false
    },

    /** fetch location of this history in the api */
    urlRoot: 'api/histories/',
    url : function(){
        //TODO: get this via url router
        return 'api/histories/' + this.get( 'history_id' ) + '/contents/' + this.get( 'id' );
    },
    
    /** Set up the model, determine if accessible, bind listeners
     *  @see Backbone.Model#initialize
     */
    //TODO:? use initialize (or validate) to check purged AND deleted -> purged XOR deleted
    initialize : function(){
        this.log( this + '.initialize', this.attributes );
        this.log( '\tparent history_id: ' + this.get( 'history_id' ) );
        
        // (curr) only handles changing state of non-accessible hdas to STATES.NOT_VIEWABLE
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

    /** Is this hda deleted or purged?
     */
    isDeletedOrPurged : function(){
        return ( this.get( 'deleted' ) || this.get( 'purged' ) );
    },

    /** based on show_deleted, show_hidden (gen. from the container control),
     *      would this ds show in the list of ds's?
     *  @param {Boolean} show_deleted are we showing deleted hdas?
     *  @param {Boolean} show_hidden are we showing hidden hdas?
     */
    //TODO: too many 'visible's
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
    
    /** Is this HDA in a 'ready' state; where 'Ready' states are states where no
     *      processing (for the ds) is left to do on the server.
     *      Currently: NEW, OK, EMPTY, FAILED_METADATA, NOT_VIEWABLE, DISCARDED,
     *      and ERROR
     */
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

    /** Convenience function to match hda.has_data.
     */
    hasData : function(){
        //TODO:?? is this equivalent to all possible hda.has_data calls?
        return ( this.get( 'file_size' ) > 0 );
    },

    /** String representation
     */
    toString : function(){
        var nameAndId = this.get( 'id' ) || '';
        if( this.get( 'name' ) ){
            nameAndId += ':"' + this.get( 'name' ) + '"';
        }
        return 'HistoryDatasetAssociation(' + nameAndId + ')';
    }
});

//------------------------------------------------------------------------------
/** Class level map of possible HDA states to their string equivalents.
 *      A port of galaxy.model.Dataset.states.
 */
HistoryDatasetAssociation.STATES = {
    // NOT ready states
    /** is uploading and not ready */
    UPLOAD              : 'upload',
    /** the job that will produce the dataset queued in the runner */
    QUEUED              : 'queued',
    /** the job that will produce the dataset paused */
    PAUSED              : 'paused',
    /** the job that will produce the dataset is running */
    RUNNING             : 'running',
    /** metadata for the dataset is being discovered/set */
    SETTING_METADATA    : 'setting_metadata',

    // ready states
    /** was created without a tool */
    NEW                 : 'new',
    /** has no data */
    EMPTY               : 'empty',
    /** has successfully completed running */
    OK                  : 'ok',

    /** metadata discovery/setting failed or errored (but otherwise ok) */
    FAILED_METADATA     : 'failed_metadata',
    /** not accessible to the current user (i.e. due to permissions) */
    NOT_VIEWABLE        : 'noPermission',   // not in trans.app.model.Dataset.states
    /** deleted while uploading */
    DISCARDED           : 'discarded',
    /** the tool producing this dataset failed */
    ERROR               : 'error'
};

//==============================================================================
/** @class Backbone collection of (HDA) models
 *
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HDACollection = Backbone.Collection.extend( LoggableMixin ).extend(
/** @lends HDACollection.prototype */{
    model           : HistoryDatasetAssociation,

    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,

    /** Set up.
     *  @see Backbone.Collection#initialize
     */
    initialize : function(){
        //this.bind( 'all', function( event ){
        //    this.log( this + '', arguments );
        //});
    },

    /** Get the ids of every hda in this collection
     *  @returns array of encoded ids 
     */
    ids : function(){
        return this.map( function( item ){ return item.id; });
    },

    /** Get every 'shown' hda in this collection based on show_deleted/hidden
     *  @param {Boolean} show_deleted are we showing deleted hdas?
     *  @param {Boolean} show_hidden are we showing hidden hdas?
     *  @returns array of hda models
     *  @see HistoryDatasetAssociation#isVisible
     */
    getVisible : function( show_deleted, show_hidden ){
        return this.filter( function( item ){ return item.isVisible( show_deleted, show_hidden ); });
    },

    /** For each possible hda state, get an array of all hda ids in that state
     *  @returns a map of states -> hda ids
     *  @see HistoryDatasetAssociation#STATES
     */
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

    /** Get the id of every hda in this collection not in a 'ready' state (running).
     *  @returns an array of hda ids
     *  @see HistoryDatasetAssociation#inReadyState
     */
    running : function(){
        var idList = [];
        this.each( function( item ){
            if( !item.inReadyState() ){
                idList.push( item.get( 'id' ) );
            }
        });
        return idList;
    },

    /** Update (fetch) the data of the hdas with the given ids.
     *  @param {String[]} ids an array of hda ids to update
     *  @see HistoryDatasetAssociation#fetch
     */
    update : function( ids ){
        this.log( this + 'update:', ids );

        if( !( ids && ids.length ) ){ return; }

        var collection = this;
        _.each( ids, function( id, index ){
            var historyItem = collection.get( id );
            historyItem.fetch();
        });
    },

    /** String representation. */
    toString : function(){
         return ( 'HDACollection(' + this.ids().join(',') + ')' );
    }
});

//==============================================================================
//return {
//    HistoryDatasetAssociation : HistoryDatasetAssociation,
//    HDACollection             : HDACollection,
//};});
