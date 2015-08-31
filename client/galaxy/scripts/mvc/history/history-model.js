define([
    "mvc/history/history-contents",
    "utils/utils",
    "mvc/base-mvc",
    "utils/localization"
], function( HISTORY_CONTENTS, UTILS, BASE_MVC, _l ){
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
        BASE_MVC.mixin( BASE_MVC.SearchableModelMixin, /** @lends History.prototype */{

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

    /** convert size in bytes to a more human readable version */
    nice_size : function(){
        return UTILS.bytesToString( this.get( 'size' ), true, 2 );
    },

    /** override to add nice_size */
    toJSON : function(){
        return _.extend( Backbone.Model.prototype.toJSON.call( this ), {
            nice_size : this.nice_size()
        });
    },

    /** override to allow getting nice_size */
    get : function( key ){
        if( key === 'nice_size' ){
            return this.nice_size();
        }
        return Backbone.Model.prototype.get.apply( this, arguments );
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

    // ........................................................................ search
    /** What model fields to search with */
    searchAttributes : [
        'name', 'annotation', 'tags'
    ],

    /** Adding title and singular tag */
    searchAliases : {
        title       : 'name',
        tag         : 'tags'
    },

    // ........................................................................ updates
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

    // ........................................................................ ajax
    /** save this history, _Mark_ing it as deleted (just a flag) */
    _delete : function( options ){
        if( this.get( 'deleted' ) ){ return jQuery.when(); }
        return this.save( { deleted: true }, options );
    },
    /** purge this history, _Mark_ing it as purged and removing all dataset data from the server */
    purge : function( options ){
        if( this.get( 'purged' ) ){ return jQuery.when(); }
        return this.save( { deleted: true, purged: true }, options );
    },
    /** save this history, _Mark_ing it as undeleted */
    undelete : function( options ){
        if( !this.get( 'deleted' ) ){ return jQuery.when(); }
        return this.save( { deleted: false }, options );
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
            copy = jQuery.post( this.urlRoot, postData );
        // if current - queue to setAsCurrent before firing 'copied'
        if( current ){
            return copy.then( function( response ){
                var newHistory = new History( response );
                return newHistory.setAsCurrent()
                    .done( function(){
                        history.trigger( 'copied', history, response );
                    });
            });
        }
        return copy.done( function( response ){
            history.trigger( 'copied', history, response );
        });
    },

    setAsCurrent : function(){
        var history = this,
            xhr = jQuery.getJSON( galaxy_config.root + 'history/set_as_current?id=' + this.id );

        xhr.done( function(){
            history.trigger( 'set-as-current', history );
        });
        return xhr;
    },

    // ........................................................................ misc
    toString : function(){
        return 'History(' + this.get( 'id' ) + ',' + this.get( 'name' ) + ')';
    }
}));

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
var ControlledFetchMixin = {

    /** Override to convert certain options keys into API index parameters */
    fetch : function( options ){
        options = options || {};
        options.data = options.data || this._buildFetchData( options );
        // use repeated params for arrays, e.g. q=1&qv=1&q=2&qv=2
        options.traditional = true;
        return Backbone.Collection.prototype.fetch.call( this, options );
    },

    /** These attribute keys are valid params to fetch/API-index */
    _fetchOptions : [
        /** model dependent string to control the order of models returned */
        'order',
        /** limit the number of models returned from a fetch */
        'limit',
        /** skip this number of models when fetching */
        'offset',
        /** what series of attributes to return (model dependent) */
        'view',
        /** individual keys to return for the models (see api/histories.index) */
        'keys'
    ],

    /** Build the data dictionary to send to fetch's XHR as data */
    _buildFetchData : function( options ){
        var data = {},
            fetchDefaults = this._fetchDefaults();
        options = _.defaults( options || {}, fetchDefaults );
        data = _.pick( options, this._fetchOptions );

        var filters = _.has( options, 'filters' )? options.filters : ( fetchDefaults.filters || {} );
        if( !_.isEmpty( filters ) ){
            _.extend( data, this._buildFetchFilters( filters ) );
        }
        return data;
    },

    /** Override to have defaults for fetch options and filters */
    _fetchDefaults : function(){
        // to be overridden
        return {};
    },

    /** Convert dictionary filters to qqv style arrays */
    _buildFetchFilters : function( filters ){
        var filterMap = {
            q  : [],
            qv : []
        };
        _.each( filters, function( v, k ){
            if( v === true ){ v = 'True'; }
            if( v === false ){ v = 'False'; }
            filterMap.q.push( k );
            filterMap.qv.push( v );
        });
        return filterMap;
    },
};

//==============================================================================
/** @class A collection of histories (per user).
 *      (stub) currently unused.
 */
var HistoryCollection = Backbone.Collection.extend( BASE_MVC.LoggableMixin ).extend( ControlledFetchMixin ).extend(
/** @lends HistoryCollection.prototype */{
    model   : History,

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    /** @type {String} the default sortOrders key for sorting */
    DEFAULT_ORDER : 'update_time',

    /** @type {Object} map of collection sorting orders generally containing a getter to return the attribute
     *      sorted by and asc T/F if it is an ascending sort.
     */
    sortOrders : {
        'update_time' : {
            getter : function( h ){ return new Date( h.get( 'update_time' ) ); },
            asc : false
        },
        'update_time-asc' : {
            getter : function( h ){ return new Date( h.get( 'update_time' ) ); },
            asc : true
        },
        'name' : {
            getter : function( h ){ return h.get( 'name' ); },
            asc : true
        },
        'name-dsc' : {
            getter : function( h ){ return h.get( 'name' ); },
            asc : false
        },
        'size' : {
            getter : function( h ){ return h.get( 'size' ); },
            asc : false
        },
        'size-asc' : {
            getter : function( h ){ return h.get( 'size' ); },
            asc : true
        }
    },

    initialize : function( models, options ){
        options = options || {};
        this.log( 'HistoryCollection.initialize', arguments );

        // instance vars
        /** @type {boolean} should deleted histories be included */
        this.includeDeleted = options.includeDeleted || false;
        // set the sort order
        this.setOrder( options.order || this.DEFAULT_ORDER );
        /** @type {String} encoded id of the history that's current */
        this.currentHistoryId = options.currentHistoryId;

        // this.on( 'all', function(){
        //    console.info( 'event:', arguments );
        // });
        this.setUpListeners();
    },

    urlRoot : ( window.galaxy_config? galaxy_config.root : '/' ) + 'api/histories',
    url     : function(){ return this.urlRoot; },

    /** returns map of default filters and settings for fetching from the API */
    _fetchDefaults : function(){
        // to be overridden
        var defaults = {
            order   : this.order,
            view    : 'detailed'
        };
        if( !this.includeDeleted ){
            defaults.filters = {
                deleted : false,
                purged  : false,
            };
        }
        return defaults;
    },

    /** set up reflexive event handlers */
    setUpListeners : function setUpListeners(){
        this.on({
            // when a history is deleted, remove it from the collection (if optionally set to do so)
            'change:deleted' : function( history ){
                // TODO: this becomes complicated when more filters are used
                this.debug( 'change:deleted', this.includeDeleted, history.get( 'deleted' ) );
                if( !this.includeDeleted && history.get( 'deleted' ) ){
                    this.remove( history );
                }
            },
            // listen for a history copy, adding it to the beginning of the collection
            'copied' : function( original, newData ){
                var history = new History( newData, [] );
                this.unshift( history );
                this.trigger( 'new-current', history, this );
            },
            // when a history is made current, track the id in the collection
            'set-as-current' : function( history ){
                var oldCurrentId = this.currentHistoryId;
                this.trigger( 'no-longer-current', oldCurrentId );
                this.currentHistoryId = history.id;
            }
        }, this );
    },

    /** override to allow passing options.order and setting the sort order to one of sortOrders */
    sort : function( options ){
        options = options || {};
        this.setOrder( options.order );
        return Backbone.Collection.prototype.sort.call( this, options );
    },

    /** build the comparator used to sort this collection using the sortOrder map and the given order key
     *  @event 'changed-order' passed the new order and the collection
     */
    setOrder : function( order ){
        var collection = this,
            sortOrder = this.sortOrders[ order ];
        if( _.isUndefined( sortOrder ) ){ return; }

        collection.order = order;
        collection.comparator = function comparator( a, b ){
            var currentHistoryId = collection.currentHistoryId;
            // current always first
            if( a.id === currentHistoryId ){ return -1; }
            if( b.id === currentHistoryId ){ return 1; }
            // then compare by an attribute
            a = sortOrder.getter( a );
            b = sortOrder.getter( b );
            return sortOrder.asc?
                ( ( a === b )?( 0 ):( a > b ?  1 : -1 ) ):
                ( ( a === b )?( 0 ):( a > b ? -1 :  1 ) );
        };
        collection.trigger( 'changed-order', collection.order, collection );
        return collection;
    },

    /** override to provide order and offsets based on instance vars, set limit if passed,
     *  and set allFetched/fire 'all-fetched' when xhr returns
     */
    fetch : function( options ){
        options = options || {};
        if( this.allFetched ){ return jQuery.when({}); }
        var collection = this,
            fetchOptions = _.defaults( options, {
                remove : false,
                offset : collection.length >= 1? ( collection.length - 1 ) : 0,
                order  : collection.order
            }),
            limit = options.limit;
        if( !_.isUndefined( limit ) ){
            fetchOptions.limit = limit;
        }

        return ControlledFetchMixin.fetch.call( this, fetchOptions )
            .done( function _postFetchMore( fetchData ){
                var numFetched = _.isArray( fetchData )? fetchData.length : 0;
                // anything less than a full page means we got all there is to get
                if( !limit || numFetched < limit ){
                    collection.allFetched = true;
                    collection.trigger( 'all-fetched', collection );
                }
            }
        );
    },

    /** create a new history and by default set it to be the current history */
    create : function create( data, hdas, historyOptions, xhrOptions ){
        //TODO: .create is actually a collection function that's overridden here
        var collection = this,
            xhr = jQuery.getJSON( galaxy_config.root + 'history/create_new_current'  );
        return xhr.done( function( newData ){
            var history = new History( newData, [], historyOptions || {} );
            // new histories go in the front
            collection.unshift( history );
            collection.trigger( 'new-current', history, this );
        });
    },

    /** override to reset allFetched flag to false */
    reset : function( models, options ){
        this.allFetched = false;
        return Backbone.Collection.prototype.reset.call( this, models, options );
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
