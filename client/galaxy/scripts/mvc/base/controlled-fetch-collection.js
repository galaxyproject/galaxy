define([
    'libs/underscore',
    'libs/backbone',
    'mvc/base-mvc',
], function( _, Backbone, BASE_MVC ){
'use strict';

//=============================================================================
/**
 * A Collection that can be limited/offset/re-ordered/filtered.
 * @type {Backbone.Collection}
 */
var ControlledFetchCollection = Backbone.Collection.extend({

    /** call setOrder on initialization to build the comparator based on options */
    initialize : function( models, options ){
        Backbone.Collection.prototype.initialize.call( this, models, options );
        this.setOrder( options.order || this.order, { silent: true });
    },

    /** set up to track order changes and re-sort when changed */
    _setUpListeners : function(){
        return this.on({
            'changed-order' : this.sort
        });
    },

    /** override to provide order and offsets based on instance vars, set limit if passed,
     *  and set allFetched/fire 'all-fetched' when xhr returns
     */
    fetch : function( options ){
        options = this._buildFetchOptions( options );
        return Backbone.Collection.prototype.fetch.call( this, options );
    },

    /** build ajax data/parameters from options */
    _buildFetchOptions : function( options ){
        // note: we normally want options passed in to override the defaults built here
        // so most of these fns will generate defaults
        options = _.clone( options ) || {};
        var self = this;

        // jquery ajax option; allows multiple q/qv for filters (instead of 'q[]')
        options.traditional = true;

        // options.data
        // we keep limit, offset, etc. in options *as well as move it into data* because:
        // - it makes fetch calling convenient to add it to a single options map (instead of as mult. args)
        // - it allows the std. event handlers (for fetch, etc.) to have access
        //   to the pagination options too
        //      (i.e. this.on( 'sync', function( options ){ if( options.limit ){ ... } }))
        // however, when we send to xhr/jquery we copy them to data also so that they become API query params
        options.data = options.data || self._buildFetchData( options );
        // console.log( 'data:', options.data );

        // options.data.filters --> options.data.q, options.data.qv
        var filters = this._buildFetchFilters( options );
        // console.log( 'filters:', filters );
        if( !_.isEmpty( filters ) ){
            _.extend( options.data, this._fetchFiltersToAjaxData( filters ) );
        }
        // console.log( 'data:', options.data );
        return options;
    },

    /** Build the dictionary to send to fetch's XHR as data */
    _buildFetchData : function( options ){
        var defaults = {};
        if( this.order ){ defaults.order = this.order; }
        return _.defaults( _.pick( options, this._fetchParams ), defaults );
    },

    /** These attribute keys are valid params to fetch/API-index */
    _fetchParams : [
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

    /** add any needed filters here based on collection state */
    _buildFetchFilters : function( options ){
        // override
        return _.clone( options.filters || {} );
    },

    /** Convert dictionary filters to qqv style arrays */
    _fetchFiltersToAjaxData : function( filters ){
        // return as a map so ajax.data can extend from it
        var filterMap = {
            q  : [],
            qv : []
        };
        _.each( filters, function( v, k ){
            // don't send if filter value is empty
            if( v === undefined || v === '' ){ return; }
            // json to python
            if( v === true ){ v = 'True'; }
            if( v === false ){ v = 'False'; }
            if( v === null ){ v = 'None'; }
            // map to k/v arrays (q/qv)
            filterMap.q.push( k );
            filterMap.qv.push( v );
        });
        return filterMap;
    },

    /** override to reset allFetched flag to false */
    reset : function( models, options ){
        this.allFetched = false;
        return Backbone.Collection.prototype.reset.call( this, models, options );
    },

    // ........................................................................ order
    order : null,

    /** @type {Object} map of collection available sorting orders containing comparator fns */
    comparators : {
        'update_time'       : BASE_MVC.buildComparator( 'update_time', { ascending: false }),
        'update_time-asc'   : BASE_MVC.buildComparator( 'update_time', { ascending: true }),
        'create_time'       : BASE_MVC.buildComparator( 'create_time', { ascending: false }),
        'create_time-asc'   : BASE_MVC.buildComparator( 'create_time', { ascending: true }),
    },

    /** set the order and comparator for this collection then sort with the new order
     *  @event 'changed-order' passed the new order and the collection
     */
    setOrder : function( order, options ){
        options = options || {};
        var collection = this;
        var comparator = collection.comparators[ order ];
        if( _.isUndefined( comparator ) ){ throw new Error( 'unknown order: ' + order ); }
        // if( _.isUndefined( comparator ) ){ return; }
        if( comparator === collection.comparator ){ return; }

        var oldOrder = collection.order;
        collection.order = order;
        collection.comparator = comparator;

        if( !options.silent ){
            collection.trigger( 'changed-order', options );
        }
        return collection;
    },
});


//==============================================================================
    return {
        ControlledFetchCollection     : ControlledFetchCollection
    };
});
