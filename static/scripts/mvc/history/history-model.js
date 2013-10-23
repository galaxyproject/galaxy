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
    //TODO: bind change events from items and collection to this (itemLengths, states)

    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,

    // values from api (may need more)
    defaults : {
        model_class     : 'History',
        id              : null,
        name            : 'Unnamed History',
        state           : 'new',

        diskSize : 0,
        deleted : false
    },

    // ........................................................................ urls
    urlRoot: galaxy_config.root + 'api/histories',

    renameUrl : function(){
//TODO: just use this.save()
        var id = this.get( 'id' );
        if( !id ){ return undefined; }
        return galaxy_config.root + 'history/rename_async?id=' + this.get( 'id' );
    },
    annotateUrl : function(){
        var id = this.get( 'id' );
        if( !id ){ return undefined; }
        return galaxy_config.root + 'history/annotate_async?id=' + this.get( 'id' );
    },
    tagUrl : function(){
        var id = this.get( 'id' );
        if( !id ){ return undefined; }
        return galaxy_config.root + 'tag/get_tagging_elt_async?item_id=' + this.get( 'id' ) + '&item_class=History';
    },

    // ........................................................................ set up/tear down
    /** Set up the hdas collection
     *  @param {Object} historyJSON model data for this History
     *  @param {Object[]} hdaJSON   array of model data for this History's HDAs
     *  @see BaseModel#initialize
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

        // set up update timeout if needed
        this.checkForUpdates();
    },

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

        // debugging events
        //if( this.logger ){
        //    this.on( 'all', function( event ){
        //        this.log( this + '', arguments );
        //    }, this );
        //}
    },

    //TODO: see base-mvc
    //onFree : function(){
    //    if( this.hdas ){
    //        this.hdas.free();
    //    }
    //},

    errorHandler : function( model, xhr, options, msg, details ){
        // clear update timeout on model err
        this.clearUpdateTimeout();
    },

    // ........................................................................ common queries
    hasUser : function(){
        var user = this.get( 'user' );
        return !!( user && user.id );
    },

    // ........................................................................ ajax
    // get the history's state from it's cummulative ds states, delay + update if needed
    // events: ready
    checkForUpdates : function( onReadyCallback ){
        //console.info( 'checkForUpdates' )

        // get overall History state from collection, run updater if History has running/queued hdas
        // boiling it down on the client to running/not
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

    setUpdateTimeout : function( delay ){
        //TODO: callbacks?
        delay = delay || History.UPDATE_DELAY;
        var history = this;

        // prevent buildup of updater timeouts by clearing previous if any, then set new and cache id
        this.clearUpdateTimeout();
        this.updateTimeoutId = setTimeout( function(){
            history.refresh();
        }, delay );
        return this.updateTimeoutId;
    },

    clearUpdateTimeout : function(){
        if( this.updateTimeoutId ){
            clearTimeout( this.updateTimeoutId );
            this.updateTimeoutId = null;
        }
    },

    // update this history, find any hda's running/queued, update ONLY those that have changed states,
    //  set up to run this again in some interval of time
    // events: ready
    refresh : function( detailIds, options ){
        //console.info( 'refresh:', detailIds, this.hdas );
        detailIds = detailIds || [];
        options = options || {};
        var history = this;

        options.data = options.data || {};
        if( detailIds.length ){
            options.data.details = detailIds.join( ',' );
        }
        var xhr = this.hdas.fetch( options );
        xhr.done( function( hdaModels ){
            //this.trigger( 'hdas-refreshed', this, hdaModels );
            history.checkForUpdates(function(){
                // fetch the history after an update in order to recalc history size
                //TODO: move to event?
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
        //return jQuery.ajax( '/generate_json_error' );
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
        //return jQuery.ajax( '/generate_json_error' );
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
        //console.warn( 'getHistoryData.localFailHandler (history)', xhr, status, message );
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
        //console.warn( 'getHistoryData.localFailHandler (hdas)', xhr, status, message );
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
