define([
    "mvc/dataset/hda-model"
], function( hdaModel ){
//==============================================================================
/** @class Model for a Galaxy history resource - both a record of user
 *      tool use and a collection of the datasets those tools produced.
 *  @name History
 *
 *  @augments Backbone.Model
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var History = Backbone.Model.extend( LoggableMixin ).extend(
/** @lends History.prototype */{

    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,

    // values from api (may need more)
    defaults : {
        model_class     : 'History',
        id              : null,
        name            : 'Unnamed History',
        state           : 'new',

        diskSize        : 0,
        deleted         : false
    },

    // ........................................................................ urls
    urlRoot: galaxy_config.root + 'api/histories',

    /** url for changing the name of the history */
    renameUrl : function(){
//TODO: just use this.save()
        var id = this.get( 'id' );
        if( !id ){ return undefined; }
        return galaxy_config.root + 'history/rename_async?id=' + this.get( 'id' );
    },
    /** url for changing the annotation of the history */
    annotateUrl : function(){
        var id = this.get( 'id' );
        if( !id ){ return undefined; }
        return galaxy_config.root + 'history/annotate_async?id=' + this.get( 'id' );
    },
    /** url for changing the tags of the history */
    tagUrl : function(){
        var id = this.get( 'id' );
        if( !id ){ return undefined; }
        return galaxy_config.root + 'tag/get_tagging_elt_async?item_id=' + this.get( 'id' ) + '&item_class=History';
    },

    // ........................................................................ set up/tear down
    /** Set up the model
     *  @param {Object} historyJSON model data for this History
     *  @param {Object[]} hdaJSON   array of model data for this History's HDAs
     *  @param {Object} options     any extra settings including logger
     */
    initialize : function( historyJSON, hdaJSON, options ){
        options = options || {};
        this.logger = options.logger || null;
        this.log( this + ".initialize:", historyJSON, hdaJSON, options );

        /** HDACollection of the HDAs contained in this history. */
        this.hdas = new hdaModel.HDACollection( hdaJSON || [], { historyId: this.get( 'id' )});
        // if we've got hdas passed in the constructor, load them
        if( hdaJSON && _.isArray( hdaJSON ) ){
            this.hdas.reset( hdaJSON );
        }

        this._setUpListeners();

        /** cached timeout id for the HDA updater */
        this.updateTimeoutId = null;
        // set up update timeout if needed
        this.checkForUpdates();
    },

    /** set up any event listeners for this history including those to the contained HDAs
     *  events: error:hdas  if an error occurred with the HDA collection
     */
    _setUpListeners : function(){
        this.on( 'error', function( model, xhr, options, msg, details ){
            this.errorHandler( model, xhr, options, msg, details );
        });

        // hda collection listening
        if( this.hdas ){
            this.listenTo( this.hdas, 'error', function(){
                this.trigger.apply( this, [ 'error:hdas' ].concat( jQuery.makeArray( arguments ) ) );
            });
        }
        // if the model's id changes ('current' or null -> an actual id), update the hdas history_id
        this.on( 'change:id', function( model, newId ){
            if( this.hdas ){
                this.hdas.historyId = newId;
            }
        }, this );
    },

    //TODO: see base-mvc
    //onFree : function(){
    //    if( this.hdas ){
    //        this.hdas.free();
    //    }
    //},

    /** event listener for errors. Generally errors are handled outside this model */
    errorHandler : function( model, xhr, options, msg, details ){
        // clear update timeout on model err
        this.clearUpdateTimeout();
    },

    // ........................................................................ common queries
    /** is this model already associated with a user? */
//TODO: remove
    hasUser : function(){
        var user = this.get( 'user' );
        return !!( user && user.id );
    },

    /** T/F is this history owned by the current user (Galaxy.currUser)
     *      Note: that this will return false for an anon user even if the history is theirs.
     */
    ownedByCurrUser : function(){
        // no currUser
        if( !Galaxy || !Galaxy.currUser ){
            return false;
        }
        // user is anon or history isn't owned
        if( Galaxy.currUser.isAnonymous() || Galaxy.currUser.id !== this.get( 'user_id' ) ){
            return false;
        }
        return true;
    },

    hdaCount : function(){
        return _.reduce( _.values( this.get( 'state_details' ) ), function( memo, num ){ return memo + num; }, 0 );
    },

    // ........................................................................ ajax
    /** does the HDA collection indicate they're still running and need to be updated later? delay + update if needed
     *  @param {Function} onReadyCallback   function to run when all HDAs are in the ready state
     *  events: ready
     */
    checkForUpdates : function( onReadyCallback ){
        //console.info( 'checkForUpdates' )

        // get overall History state from collection, run updater if History has running/queued hdas
        //  boiling it down on the client to running/not
        if( this.hdas.running().length ){
            this.setUpdateTimeout();

        } else {
            this.trigger( 'ready' );
            if( _.isFunction( onReadyCallback ) ){
                onReadyCallback.call( this );
            }
        }
        return this;
    },

    /** create a timeout (after UPDATE_DELAY or delay ms) to refetch the HDA collection. Clear any prev. timeout */
    setUpdateTimeout : function( delay ){
        delay = delay || History.UPDATE_DELAY;
        var history = this;

        // prevent buildup of updater timeouts by clearing previous if any, then set new and cache id
        this.clearUpdateTimeout();
        this.updateTimeoutId = setTimeout( function(){
            history.refresh();
        }, delay );
        return this.updateTimeoutId;
    },

    /** clear the timeout and the cached timeout id */
    clearUpdateTimeout : function(){
        if( this.updateTimeoutId ){
            clearTimeout( this.updateTimeoutId );
            this.updateTimeoutId = null;
        }
    },

    /* update the HDA collection getting full detailed model data for any hda whose id is in detailIds
     *  set up to run this again in some interval of time
     *  @param {String[]} detailIds list of HDA ids to get detailed model data for
     *  @param {Object} options     std. backbone fetch options map
     */
    refresh : function( detailIds, options ){
        //console.info( 'refresh:', detailIds, this.hdas );
        detailIds = detailIds || [];
        options = options || {};
        var history = this;

        // add detailIds to options as CSV string
        options.data = options.data || {};
        if( detailIds.length ){
            options.data.details = detailIds.join( ',' );
        }
        var xhr = this.hdas.fetch( options );
        xhr.done( function( hdaModels ){
            history.checkForUpdates( function(){
                // fetch the history inside onReadyCallback in order to recalc history size
                this.fetch();
            });
        });
        return xhr;
    },

    // ........................................................................ misc
    toString : function(){
        return 'History(' + this.get( 'id' ) + ',' + this.get( 'name' ) + ')';
    }
});

//------------------------------------------------------------------------------ CLASS VARS
/** When the history has running hdas,
 *  this is the amount of time between update checks from the server
 */
History.UPDATE_DELAY = 4000;

/** Get data for a history then it's hdas using a sequential ajax call, return a deferred to receive both */
History.getHistoryData = function getHistoryData( historyId, options ){
    options = options || {};
    var hdaDetailIds = options.hdaDetailIds || [];
    //console.debug( 'getHistoryData:', historyId, options );

    var df = jQuery.Deferred(),
        historyJSON = null;

    function getHistory( id ){
        // get the history data
        return jQuery.ajax( galaxy_config.root + 'api/histories/' + historyId );
    }
    function countHdasFromHistory( historyData ){
        // get the number of hdas accrd. to the history
        if( !historyData || !historyData.state_ids ){ return 0; }
        return _.reduce( historyData.state_ids, function( memo, list, state ){
            return memo + list.length;
        }, 0 );
    }
    function getHdas( historyData ){
        // get the hda data
        // if no hdas accrd. to history: return empty immed.
        if( !countHdasFromHistory( historyData ) ){ return []; }
        // if there are hdas accrd. to history: get those as well
        if( _.isFunction( hdaDetailIds ) ){
            hdaDetailIds = hdaDetailIds( historyData );
        }
        var data = ( hdaDetailIds.length )?( { details : hdaDetailIds.join( ',' ) } ):( {} );
        return jQuery.ajax( galaxy_config.root + 'api/histories/' + historyData.id + '/contents', { data: data });
    }

    // getting these concurrently is 400% slower (sqlite, local, vanilla) - so:
    //  chain the api calls - getting history first then hdas

    var historyFn = options.historyFn || getHistory,
        hdaFn = options.hdaFn || getHdas;

    // chain ajax calls: get history first, then hdas
    var historyXHR = historyFn( historyId );
    historyXHR.done( function( json ){
        // set outer scope var here for use below
        historyJSON = json;
        df.notify({ status: 'history data retrieved', historyJSON: historyJSON });
    });
    historyXHR.fail( function( xhr, status, message ){
        // call reject on the outer deferred to allow it's fail callback to run
        df.reject( xhr, 'loading the history' );
    });

    var hdaXHR = historyXHR.then( hdaFn );
    hdaXHR.then( function( hdaJSON ){
        df.notify({ status: 'dataset data retrieved', historyJSON: historyJSON, hdaJSON: hdaJSON });
        // we've got both: resolve the outer scope deferred
        df.resolve( historyJSON, hdaJSON );
    });
    hdaXHR.fail( function( xhr, status, message ){
        // call reject on the outer deferred to allow it's fail callback to run
        df.reject( xhr, 'loading the datasets', { history: historyJSON } );
    });

    return df;
};


//==============================================================================
/** @class A collection of histories (per user).
 *      (stub) currently unused.
 *  @name HistoryCollection
 *
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HistoryCollection = Backbone.Collection.extend( LoggableMixin ).extend(
/** @lends HistoryCollection.prototype */{
    model   : History,
    urlRoot : galaxy_config.root + 'api/histories'
    
    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,
});

//==============================================================================
return {
    History           : History,
    HistoryCollection : HistoryCollection
};});
