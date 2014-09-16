define([
    "mvc/history/history-contents",
    "mvc/base-mvc",
    "utils/localization"
], function( HISTORY_CONTENTS, BASE_MVC, _l ){
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
var History = Backbone.Model.extend( BASE_MVC.LoggableMixin ).extend(
/** @lends History.prototype */{

    /** logger used to record this.log messages, commonly set to console */
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

    // ........................................................................ set up/tear down
    /** Set up the model
     *  @param {Object} historyJSON model data for this History
     *  @param {Object[]} contentsJSON   array of model data for this History's contents (hdas or collections)
     *  @param {Object} options     any extra settings including logger
     */
    initialize : function( historyJSON, contentsJSON, options ){
        options = options || {};
        this.logger = options.logger || null;
        this.log( this + ".initialize:", historyJSON, contentsJSON, options );

        /** HistoryContents collection of the HDAs contained in this history. */
        this.log( 'creating history contents:', contentsJSON );
        this.contents = new HISTORY_CONTENTS.HistoryContents( contentsJSON || [], { historyId: this.get( 'id' )});
        //// if we've got hdas passed in the constructor, load them
        //if( contentsJSON && _.isArray( contentsJSON ) ){
        //    this.log( 'resetting history contents:', contentsJSON );
        //    this.contents.reset( contentsJSON );
        //}

        this._setUpListeners();

        /** cached timeout id for the dataset updater */
        this.updateTimeoutId = null;
        // set up update timeout if needed
        //this.checkForUpdates();
    },

    /** set up any event listeners for this history including those to the contained HDAs
     *  events: error:contents  if an error occurred with the contents collection
     */
    _setUpListeners : function(){
        this.on( 'error', function( model, xhr, options, msg, details ){
            this.errorHandler( model, xhr, options, msg, details );
        });

        // hda collection listening
        if( this.contents ){
            this.listenTo( this.contents, 'error', function(){
                this.trigger.apply( this, [ 'error:contents' ].concat( jQuery.makeArray( arguments ) ) );
            });
        }
        // if the model's id changes ('current' or null -> an actual id), update the contents history_id
        this.on( 'change:id', function( model, newId ){
            if( this.contents ){
                this.contents.historyId = newId;
            }
        }, this );
    },

    //TODO: see base-mvc
    //onFree : function(){
    //    if( this.contents ){
    //        this.contents.free();
    //    }
    //},

    /** event listener for errors. Generally errors are handled outside this model */
    errorHandler : function( model, xhr, options, msg, details ){
        // clear update timeout on model err
        this.clearUpdateTimeout();
    },

    // ........................................................................ common queries
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

    /**  */
    contentsCount : function(){
        return _.reduce( _.values( this.get( 'state_details' ) ), function( memo, num ){ return memo + num; }, 0 );
    },

    // ........................................................................ ajax
    /** does the contents collection indicate they're still running and need to be updated later?
     *      delay + update if needed
     *  @param {Function} onReadyCallback   function to run when all contents are in the ready state
     *  events: ready
     */
    checkForUpdates : function( onReadyCallback ){
        //this.info( 'checkForUpdates' )

        // get overall History state from collection, run updater if History has running/queued contents
        //  boiling it down on the client to running/not
        if( this.contents.running().length ){
            this.setUpdateTimeout();

        } else {
            this.trigger( 'ready' );
            if( _.isFunction( onReadyCallback ) ){
                onReadyCallback.call( this );
            }
        }
        return this;
    },

    /** create a timeout (after UPDATE_DELAY or delay ms) to refetch the contents. Clear any prev. timeout */
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

    /* update the contents, getting full detailed model data for any whose id is in detailIds
     *  set up to run this again in some interval of time
     *  @param {String[]} detailIds list of content ids to get detailed model data for
     *  @param {Object} options     std. backbone fetch options map
     */
    refresh : function( detailIds, options ){
        //this.info( 'refresh:', detailIds, this.contents );
        detailIds = detailIds || [];
        options = options || {};
        var history = this;

        // add detailIds to options as CSV string
        options.data = options.data || {};
        if( detailIds.length ){
            options.data.details = detailIds.join( ',' );
        }
        var xhr = this.contents.fetch( options );
        xhr.done( function( models ){
            history.checkForUpdates( function(){
                // fetch the history inside onReadyCallback in order to recalc history size
                this.fetch();
            });
        });
        return xhr;
    },

    /** Make a copy of this history on the server
     *  @param {Boolean} current    if true, set the copy as the new current history (default: true)
     *  @param {String} name        name of new history (default: none - server sets to: Copy of <current name>)
     *  @fires copied               passed this history and the response JSON from the copy
     *  @returns {xhr}
     */
    copy : function( current, name ){
        current = ( current !== undefined )?( current ):( true );
        if( !this.id ){
            throw new Error( 'You must set the history ID before copying it.' );
        }

        var postData = { history_id  : this.id };
        if( current ){
            postData.current = true;
        }
        if( name ){
            postData.name = name;
        }

        //TODO:?? all datasets?

        var history = this,
            xhr = jQuery.post( this.urlRoot, postData );
        xhr.done( function( newData ){
            history.trigger( 'copied', history, newData );
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

/** Get data for a history then its hdas using a sequential ajax call, return a deferred to receive both */
History.getHistoryData = function getHistoryData( historyId, options ){
    options = options || {};
    var detailIdsFn = options.detailIdsFn || [];
    var hdcaDetailIds = options.hdcaDetailIds || [];
    //console.debug( 'getHistoryData:', historyId, options );

    var df = jQuery.Deferred(),
        historyJSON = null;

    function getHistory( id ){
        // get the history data
        if( historyId === 'current' ){
            return jQuery.getJSON( galaxy_config.root + 'history/current_history_json' );
        }
        return jQuery.ajax( galaxy_config.root + 'api/histories/' + historyId );
    }
    function isEmpty( historyData ){
        // get the number of hdas accrd. to the history
        return historyData && historyData.empty;
    }
    function getContents( historyData ){
        // get the hda data
        // if no hdas accrd. to history: return empty immed.
        if( isEmpty( historyData ) ){ return []; }
        // if there are hdas accrd. to history: get those as well
        if( _.isFunction( detailIdsFn ) ){
            detailIdsFn = detailIdsFn( historyData );
        }
        if( _.isFunction( hdcaDetailIds ) ){
            hdcaDetailIds = hdcaDetailIds( historyData );
        }
        var data = {};
        if( detailIdsFn.length ) {
            data.dataset_details = detailIdsFn.join( ',' );
        }
        if( hdcaDetailIds.length ) {
            // for symmetry, not actually used by backend of consumed
            // by frontend.
            data.dataset_collection_details = hdcaDetailIds.join( ',' );
        }
        return jQuery.ajax( galaxy_config.root + 'api/histories/' + historyData.id + '/contents', { data: data });
    }

    // getting these concurrently is 400% slower (sqlite, local, vanilla) - so:
    //  chain the api calls - getting history first then contents

    var historyFn = options.historyFn || getHistory,
        contentsFn = options.contentsFn || getContents;

    // chain ajax calls: get history first, then hdas
    var historyXHR = historyFn( historyId );
    historyXHR.done( function( json ){
        // set outer scope var here for use below
        historyJSON = json;
        df.notify({ status: 'history data retrieved', historyJSON: historyJSON });
    });
    historyXHR.fail( function( xhr, status, message ){
        // call reject on the outer deferred to allow its fail callback to run
        df.reject( xhr, 'loading the history' );
    });

    var contentsXHR = historyXHR.then( contentsFn );
    contentsXHR.then( function( contentsJSON ){
        df.notify({ status: 'contents data retrieved', historyJSON: historyJSON, contentsJSON: contentsJSON });
        // we've got both: resolve the outer scope deferred
        df.resolve( historyJSON, contentsJSON );
    });
    contentsXHR.fail( function( xhr, status, message ){
        // call reject on the outer deferred to allow its fail callback to run
        df.reject( xhr, 'loading the contents', { history: historyJSON } );
    });

    return df;
};


//==============================================================================
/** @class A collection of histories (per user).
 *      (stub) currently unused.
 */
var HistoryCollection = Backbone.Collection.extend( BASE_MVC.LoggableMixin ).extend(
/** @lends HistoryCollection.prototype */{
    model   : History,
    
    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    urlRoot : ( window.galaxy_config? galaxy_config.root : '/' ) + 'api/histories',
    //url     : function(){ return this.urlRoot; },

    initialize : function( models, options ){
        options = options || {};
        this.log( 'HistoryCollection.initialize', arguments );
        this.includeDeleted = options.includeDeleted || false;

        //this.on( 'all', function(){
        //    console.info( 'event:', arguments );
        //});

        this.setUpListeners();
    },

    setUpListeners : function setUpListeners(){
        var collection = this;

        // when a history is deleted, remove it from the collection (if optionally set to do so)
        this.on( 'change:deleted', function( history ){
            this.debug( 'change:deleted', collection.includeDeleted, history.get( 'deleted' ) );
            if( !collection.includeDeleted && history.get( 'deleted' ) ){
                collection.remove( history );
            }
        });

        // listen for a history copy, adding it to the beginning of the collection
        this.on( 'copied', function( original, newData ){
            this.unshift( new History( newData, [] ) );
        });
    },

    create : function create( data, hdas, historyOptions, xhrOptions ){
        var collection = this,
            history = new History( data || {}, hdas || [], historyOptions || {} );
        return history.save( xhrOptions ).done( function( newData ){
            // new histories go in the front
//TODO:  (implicit ordering by update time...)
            collection.unshift( history );
        });
    },

    toString: function toString(){
        return 'HistoryCollection(' + this.length + ')';
    }
});

//==============================================================================
return {
    History           : History,
    HistoryCollection : HistoryCollection
};});
