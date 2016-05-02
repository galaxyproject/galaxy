define([
    "mvc/base/controlled-fetch-collection",
    "mvc/history/hda-model",
    "mvc/history/hdca-model",
    "mvc/history/history-preferences",
    "mvc/base-mvc",
    "utils/ajax-queue"
], function( CONTROLLED_FETCH_COLLECTION, HDA_MODEL, HDCA_MODEL, HISTORY_PREFS, BASE_MVC, AJAX_QUEUE ){
'use strict';

//==============================================================================
var _super = CONTROLLED_FETCH_COLLECTION.ControlledFetchCollection;
// var _super = CONTROLLED_FETCH_COLLECTION.PaginatedCollection;
// var _super = CONTROLLED_FETCH_COLLECTION.InfinitelyScrollingCollection;
/** @class Backbone collection for history content.
 *      NOTE: history content seems like a dataset collection, but differs in that it is mixed:
 *          each element can be either an HDA (dataset) or a DatasetCollection and co-exist on
 *          the same level.
 *      Dataset collections on the other hand are not mixed and (so far) can only contain either
 *          HDAs or child dataset collections on one level.
 *      This is why this does not inherit from any of the DatasetCollections (currently).
 */
var HistoryContents = _super.extend( BASE_MVC.LoggableMixin ).extend({
    _logNamespace : 'history',

    /** since history content is a mix, override model fn into a factory, creating based on history_content_type */
    model : function( attrs, options ) {
        if( attrs.history_content_type === "dataset" ) {
            return new HDA_MODEL.HistoryDatasetAssociation( attrs, options );

        } else if( attrs.history_content_type === "dataset_collection" ) {
            switch( attrs.collection_type ){
                case 'list':
                    return new HDCA_MODEL.HistoryListDatasetCollection( attrs, options );
                case 'paired':
                    return new HDCA_MODEL.HistoryPairDatasetCollection( attrs, options );
                case 'list:paired':
                    return new HDCA_MODEL.HistoryListPairedDatasetCollection( attrs, options );
            }
            // This is a hack inside a hack:
            // Raise a plain object with validationError to fake a model.validationError
            // (since we don't have a model to use validate with)
            // (the outer hack being the mixed content/model function in this collection)
            return { validationError : 'Unknown collection_type: ' + attrs.history_content_type };
        }
        return { validationError : 'Unknown history_content_type: ' + attrs.history_content_type };
    },

    /** @type {Number} limit used for the first fetch (or a reset) */
    limitOnFirstFetch   : 500,
    /** @type {Number} limit used for each subsequent fetch */
    limitPerFetch       : 500,

    /** @type {String} order used here and when fetching from server */
    order : 'hid',

    /** Set up */
    initialize : function( models, options ){
        options = options || {};
        _super.prototype.initialize.call( this, models, options );

        this.history = options.history || null;
        this.historyId = options.historyId || null;

        // backbonejs uses collection.model.prototype.idAttribute to determine if a model is *already* in a collection
        //  and either merged or replaced. In this case, our 'model' is a function so we need to add idAttribute
        //  manually here - if we don't, contents will not merge but be replaced/swapped.
        this.model.prototype.idAttribute = 'type_id';

        /** @type {Boolean} does this collection contain and fetch deleted elements */
        this.includeDeleted = options.includeDeleted || false;
        /** @type {Boolean} does this collection contain and fetch non-visible elements */
        this.includeHidden = options.includeHidden || false;

        this.on( 'all', function(){
            var args = _.toArray( arguments );
            if( /^change:*/.test( args[0] ) ){ return; }
            console.log.apply( console, [ this + '' ].concat( args ) );
        });
    },

    /** root api url */
    urlRoot : Galaxy.root + 'api/histories',

    /** complete api url */
    url : function(){
        return this.urlRoot + '/' + this.historyId + '/contents';
    },

    // ........................................................................ common queries
    /** @type {Object} map of collection available sorting orders containing comparator fns */
    comparators : _.extend( _.clone( _super.prototype.comparators ), {
        'name'       : BASE_MVC.buildComparator( 'name', { ascending: true }),
        'name-dsc'   : BASE_MVC.buildComparator( 'name', { ascending: false }),
        'hid'        : BASE_MVC.buildComparator( 'hid',  { ascending: false }),
        'hid-asc'    : BASE_MVC.buildComparator( 'hid',  { ascending: true }),
    }),

    /** Get every model in this collection not in a 'ready' state (running). */
    running : function(){
        return this.filter( function( c ){ return !c.inReadyState(); });
    },

    /**  */
    runningAndActive : function(){
        return this.filter( function( c ){
            return ( !c.inReadyState() )
                && (  c.get( 'visible' ) )
                // TODO: deletedOrPurged?
                && ( !c.get( 'deleted' ) );
        });
    },

    /** Get the model with the given hid
     *  @param {Int} hid the hid to search for
     *  @returns {HistoryDatasetAssociation} the model with the given hid or undefined if not found
     */
    getByHid : function( hid ){
        return _.first( this.filter( function( c ){ return c.get( 'hid' ) === hid; }) );
    },

    /** return true if all contents have details */
    haveDetails : function(){
        return this.all( function( c ){ return c.hasDetails(); });
    },

    // ........................................................................ hidden / deleted
    /** return a new contents collection of only hidden items */
    hidden : function(){
        return this.filter( function( c ){ return c.hidden(); });
    },

    /** return a new contents collection of only hidden items */
    deleted : function(){
        return this.filter( function( c ){ return c.get( 'deleted' ); });
    },

    /** return a new contents collection of only hidden items */
    visibleAndUndeleted : function(){
        return this.filter( function( c ){
            return (  c.get( 'visible' ) )
                // TODO: deletedOrPurged?
                && ( !c.get( 'deleted' ) );
        });
    },

    /** create a setter in order to publish the change */
    setIncludeDeleted : function( setting ){
        if( _.isBoolean( setting ) && setting !== this.includeDeleted ){
            this.includeDeleted = setting;
            this.trigger( 'change:include-deleted', setting, this );
        }
    },

    /** create a setter in order to publish the change */
    setIncludeHidden : function( setting ){
        if( _.isBoolean( setting ) && setting !== this.includeHidden ){
            this.includeHidden = setting;
            this.trigger( 'change:include-hidden', setting, this );
        }
    },

    // ........................................................................ ajax
    /** override to get expanded ids from sessionStorage and pass to API as details */
    fetch : function( options ){
        options = options || {};
        if( this.historyId && !options.details ){
            var prefs = HISTORY_PREFS.HistoryPrefs.get( this.historyId ).toJSON();
            options.details = _.values( prefs.expandedIds ).join( ',' );
        }
        return _super.prototype.fetch.call( this, options );
    },

    // ............. ControlledFetch stuff
    /** override to include the API versioning flag */
    _buildFetchData : function( options ){
        return _.extend( _super.prototype._buildFetchData.call( this, options ), {
            v : 'dev'
        });
    },

    /** Extend to include details and version */
    _fetchParams : _super.prototype._fetchParams.concat([
        // TODO: remove (the need for) both
        /** version */
        'v',
        /** dataset ids to get full details of */
        'details',
    ]),

    /** override to add deleted/hidden filters */
    _buildFetchFilters : function( options ){
        var superFilters = _super.prototype._buildFetchFilters.call( this, options ) || {};
        var filters = {};
        if( !this.includeDeleted ){
            filters.deleted = false;
            filters.purged = false;
        }
        if( !this.includeHidden ){
            filters.visible = true;
        }
        return _.defaults( superFilters, filters );
    },

    /** override to filter requested contents to those updated after the Date 'since' */
    fetchUpdated : function( since, options ){
        if( since ){
            options = options || { filters: {} };
            options.remove = false;
            options.filters = {
                'update_time-ge' : since.toISOString(),
                // workflows will produce hidden datasets (non-output datasets) that still
                // need to be updated in the collection or they'll update forever
                // we can remove the default visible filter by using an 'empty' value
                visible          : ''
            };
        }
        return this.fetch( options );
    },

    /** fetch all the deleted==true contents of this collection */
    fetchDeleted : function( options ){
        options = options || {};
        var self = this;
        options.filters = _.extend( options.filters, {
            // all deleted, purged or not
            deleted : true,
            purged  : undefined
        });
        options.remove = false;

        self.trigger( 'fetching-deleted', self );
        return self.fetch( options )
            .always( function(){ self.trigger( 'fetching-deleted-done', self ); });
    },

    /** fetch all the visible==false contents of this collection */
    fetchHidden : function( options ){
        options = options || {};
        var self = this;
        options.filters = _.extend( options.filters, {
            visible : false
        });
        options.remove = false;

        self.trigger( 'fetching-hidden', self );
        return self.fetch( options )
            .always( function(){ self.trigger( 'fetching-hidden-done', self ); });
    },

    /** fetch detailed model data for all contents in this collection */
    fetchAllDetails : function( options ){
        options = options || {};
        var detailsFlag = { details: 'all' };
        options.data = _.extend( options.data || {}, detailsFlag );
        return this.fetch( options );
    },

    // ............. quasi-batch ops
    // TODO: to batch
    /** helper that fetches using filterParams then calls save on each fetched using updateWhat as the save params */
    _filterAndUpdate : function( filterParams, updateWhat ){
        var self = this;
        var idAttribute = self.model.prototype.idAttribute;
        var updateArgs = [ updateWhat ];

        return self.fetch({ filters: filterParams, remove: false })
            .then( function( fetched ){
                // convert filtered json array to model array
                fetched = fetched.reduce( function( modelArray, currJson, i ){
                    var model = self.get( currJson[ idAttribute ] );
                    return model? modelArray.concat( model ) : modelArray;
                }, []);
                return self.ajaxQueue( 'save', updateArgs, fetched );
            });
    },

    /** using a queue, perform ajaxFn on each of the models in this collection */
    ajaxQueue : function( ajaxFn, args, collection ){
        collection = collection || this.models;
        return new AJAX_QUEUE.AjaxQueue( collection.slice().reverse().map( function( content, i ){
            var fn = _.isString( ajaxFn )? content[ ajaxFn ] : ajaxFn;
            return function(){ return fn.apply( content, args ); };
        })).start();
    },

    /** @type {Integer} how many contents per call to fetch when using progressivelyFetchDetails */
    limitPerProgressiveFetch : 500,

    /** fetch contents' details in batches of limitPerCall - note: only get searchable details here */
    progressivelyFetchDetails : function( options ){
        // console.log( 'progressivelyFetchDetails:', options );
        options = options || {};
        var deferred = jQuery.Deferred();
        var self = this;
        var limit = options.limitPerCall || self.limitPerProgressiveFetch;
        // TODO: only fetch tags and annotations if specifically requested
        var searchAttributes = HDA_MODEL.HistoryDatasetAssociation.prototype.searchAttributes;
        var detailKeys = searchAttributes.join( ',' );

        // TODO: remove the need to maintain allFetched/lastFetched here
        // by using fetchFirst/More here
        function _notifyAndContinue( response, offset ){
            // console.log( 'rcvd:', response.length );
            deferred.notify( response, limit, offset );
            if( self.allFetched ){
                deferred.resolve( response, limit, offset );
                return;
            }
            _recursivelyFetch( offset + limit );
        }

        function _recursivelyFetch( offset ){
            offset = offset || 0;
            // console.log( '_recursivelyFetch:', offset );
            var _options = _.extend( _.clone( options ), {
                view    : 'summary',
                keys    : detailKeys,
                limit   : limit,
                offset  : offset,
                reset   : offset === 0
            });
            var fetchFn = offset === 0? self.fetchFirst : self.fetchMore;
            // console.log( 'fetching:', _options.limit, _options.offset );
            _.defer( function(){
                fetchFn.call( self, _options )
                    .fail( deferred.reject )
                    .done( function( r ){ _notifyAndContinue( r, offset ); });
            });
        }
        _recursivelyFetch();
        return deferred;
    },

    /** does some bit of JSON represent something that can be copied into this contents collection */
    isCopyable : function( contentsJSON ){
        var copyableModelClasses = [
            'HistoryDatasetAssociation',
            'HistoryDatasetCollectionAssociation'
        ];
        return ( ( _.isObject( contentsJSON ) && contentsJSON.id )
              && ( _.contains( copyableModelClasses, contentsJSON.model_class ) ) );
    },

    /** copy an existing, accessible hda into this collection */
    copy : function( json ){
        // TODO: somehow showhorn all this into 'save'
        var id, type, contentType;
        if( _.isString( json ) ){
            id = json;
            contentType = 'hda';
            type = 'dataset';
        } else {
            id = json.id;
            contentType = ({
                'HistoryDatasetAssociation' : 'hda',
                'LibraryDatasetDatasetAssociation' : 'ldda',
                'HistoryDatasetCollectionAssociation' : 'hdca'
            })[ json.model_class ] || 'hda';
            type = ( contentType === 'hdca'? 'dataset_collection' : 'dataset' );
        }
        var collection = this,
            xhr = jQuery.post( this.url(), {
                content : id,
                source  : contentType,
                type    : type,
                view    : 'detailed',
                keys    : 'create_time,update_time'
            })
            .done( function( response ){
                collection.add([ response ], { parse: true });
            })
            .fail( function( error, status, message ){
                collection.trigger( 'error', collection, xhr, {},
                    'Error copying contents', { type: type, id: id, source: contentType });
            });
        return xhr;
    },

    /** create a new HDCA in this collection */
    createHDCA : function( elementIdentifiers, collectionType, name, options ){
        //precondition: elementIdentifiers is an array of plain js objects
        //  in the proper form to create the collectionType
        return hdca.create({
                history_id          : this.historyId,
                collection_type     : collectionType,
                name                : name,
                // should probably be able to just send in a bunch of json here and restruct per class
                // note: element_identifiers is now (incorrectly) an attribute
                element_identifiers : elementIdentifiers
            // do not create the model on the client until the ajax returns
            }, { wait: true });
    },

    // ........................................................................ searching
    /** return true if all contents have the searchable attributes */
    haveSearchDetails : function(){
        return this.allFetched && this.all( function( content ){
            // null (which is a valid returned annotation value)
            // will return false when using content.has( 'annotation' )
            //TODO: a bit hacky - formalize
            return _.has( content.attributes, 'annotation' );
        });
    },

    /** return a new collection of contents whose attributes contain the substring matchesWhat */
    matches : function( matchesWhat ){
        return this.filter( function( content ){
            return content.matches( matchesWhat );
        });
    },

    // ........................................................................ misc
    /** In this override, copy the historyId to the clone */
    clone : function(){
        var clone = Backbone.Collection.prototype.clone.call( this );
        clone.historyId = this.historyId;
        return clone;
    },

    /** String representation. */
    toString : function(){
         return ([ 'HistoryContents(', [ this.historyId, this.length ].join(), ')' ].join( '' ));
    }
});


//==============================================================================
var HidSectionedHistoryContents = HistoryContents.extend({
    // /** @type {Number} limit used for the first fetch (or a reset) */
    // limitOnFirstFetch   : 500,
    // /** @type {Number} limit used for each subsequent fetch */
    // limitPerFetch       : 500,

    /** @type {String} order used here and when fetching from server */
    order : 'hid',

    /** Set up */
    initialize : function( models, options ){
        HistoryContents.prototype.initialize.call( this, models, options );
        // this.currentSection = null;
        this.currentSection = 0;
        this.sectionsFetched = [];
    },

    // ........................................................................ common queries
    /** @type {Object} restrict to hid ordering only */
    comparators : {
        'hid'        : BASE_MVC.buildComparator( 'hid',  { ascending: false }),
        'hid-asc'    : BASE_MVC.buildComparator( 'hid',  { ascending: true }),
    },

    /**  */
    _getLastHid : function(){
        return ( this.history.get( 'hid_counter' ) || 1 ) - 1;
    },

    /**  */
    _mapSectionRanges : function( mapFn ){
        var self = this;
        var sectionCount = self._countSections();
        var sectionNumbers = _.range( sectionCount );
        if( this.order === 'hid' ){
            sectionNumbers.reverse();
        }
        // console.log( '_mapSectionRanges:', sectionCount, sectionNumbers );
        return sectionNumbers.map( function( sectionNumber ){
            return mapFn( _.extend( self._getSectionRange( sectionNumber ), {
                number: sectionNumber,
            }));
        });
    },

    /**  */
    _countSections : function(){
        // always have at least one section
        return Math.max( 1, Math.floor( this._getLastHid() / this.hidsPerSection ) );
    },

    _lastSection : function(){
        return Math.max( 0, this._countSections() - 1 );
    },

    /**  */
    _lastFullSection : function(){
        // console.log( '_lastFullSection:' );
        var count = this._countSections();
        // console.log( '_lastFullSection, count:', count );
        // console.log( '_lastFullSection, hid:', this._getLastHid(), this.hidsPerSection, ( this._getLastHid() % this.hidsPerSection ) );
        var hasNonFullSection = ( this._getLastHid() % this.hidsPerSection ) > 0;
        // console.log( '_lastFullSection, hasNonFullSection:', hasNonFullSection );
        // console.log( '_lastFullSection:', hasNonFullSection? ( count - 1 ) : count );
        return hasNonFullSection? ( count - 1 ) : count;
    },

    /**  */
    _getSectionRange : function( sectionNumber ){
        // note: ranges are both first and last inclusive
        var lastHid = this._getLastHid();
        var hidsPerSection = this.hidsPerSection;
        var first = sectionNumber * hidsPerSection;
        var last  = sectionNumber === this._lastSection()? lastHid : ( first + hidsPerSection - 1 );
        return {
            first : first,
            last  : last
        };
    },

    /** Filter the collection to only those models that should be currently viewed */
    _filterSectionCollection : function( section, filterFn ){
        return this._sectionCollection( section ).filter( filterFn );
    },

    /**  */
    _sectionCollection : function( section ){
        // preconditon: assumes collection *has loaded* the range and is sorted
        var self = this;
        var range = self._getSectionRange( section );
        // console.log( 'range:', range );
        var descending = this.order === 'hid';
        // console.log( 'descending:', descending );

        var subcollection = [];
        var startingIndex = self._indexOfHid( descending? range.last : range.first );
        // console.log( 'startingIndex:', startingIndex );
        for( var index = startingIndex; index < this.length; index++ ){
            var content = this.at( index );
            var hid = content.get( 'hid' );

            if( descending ){
                if( hid < range.first ){ console.log( '< first' ); break; }
            } else {
                if( hid > range.last  ){ console.log( '> last' ); break; }
            }
            subcollection.push( content );
        }
        return subcollection;
    },

    _indexOfHid : function( hid ){
        return this._indexOfHidInModelArray( hid, this.models, { descending: this.order === 'hid' });
    },

    _indexOfHidInModelArray : function( hid, modelArray, options ){
        var descending = _.result( options, 'descending', true );
        function test( index ){
            var otherHid = modelArray[ index ].get( 'hid' );
            return descending? ( otherHid > hid ):( otherHid < hid );
        }
        return this._binarySearch({
            low     : 0,
            high    : modelArray.length,
            testFn  : test
        });
    },

    _binarySearch : function( options ){
        // preconditon: assumes collection is sorted
        var low = options.low, high = options.high;
        while( low < high ){
            var mid = Math.floor( ( low + high ) / 2 );
            if( options.testFn( mid ) ){
                low = mid + 1;
            } else {
                high = mid;
            }
        }
        return low;
    },

    /**  */
    _indexOfHidInSection : function( hid, section ){
        // preconditon: assumes section has been loaded and that collection is sorted
        var self = this;
        var range = self._getSectionRange( section );
        var lastSection = section === self._lastSection();
        var descending = this.order === 'hid';
        // console.log( '_indexOfHidInSection:', hid, section, range, lastSection, descending );
        var pastEndOfClosedSection = !lastSection && hid > range.last;
        if( pastEndOfClosedSection || hid < range.first ){ return null; }
        return self._indexOfHid( hid );
    },

    /**  */
    _getCurrentSectionRange : function(){
        return this._getSectionRange( this.currentSection );
    },

    /**  */
    _filterCurrentSectionCollection : function( filterFn ){
        return this._filterSectionCollection( this.currentSection, filterFn );
    },

    // ------------------------------------------------------------------------ sectioned fetching
    /** @type {Integer} number of contents/hid entries per section/page displayed */
    hidsPerSection : 100,

    fetchFirst : function( options ){
_.extend( options || {}, { silent: true });
        // console.log( 'fetchFirst?' );
        this.currentSection = 0;
        if( this.order === 'hid' && this._countSections() > 1 ){
            this.currentSection = this._lastFullSection();
        }
        // console.log( 'currentSection', this.currentSection );
        return this.fetchSection( this.currentSection, options );
    },

    fetchSection : function( section, options ){
        options = options || {};
        // console.log( this + '.fetchSection:', section, options );
        if( !options.bypassCache && _.contains( this.sectionsFetched, section, this ) ){
            this.trigger( 'fetching-section-done', section, this );
            return jQuery.when();
        }

        var self = this;
        self.trigger( 'fetching-section', section, self );

        var range = self._getSectionRange( section );
        // console.log( this + '.fetchSection:', range );
        return self.fetch( _.extend( options, {
silent: true,
            remove: false,
            filters: _.extend( options.filters || {}, {
                'hid-ge' : Math.max( range.first - 1, 0 ),
                'hid-le' : range.last
            })

        })).always( function(){
            self.trigger( 'fetching-section-done', section, self );

        }).done( function(){
            self.sectionsFetched.push( section );
            self.sectionsFetched.sort();
        });
    },

    fetchDeletedInSection : function( section, options ){
        options = options || {};
        var self = this;
        options.filters = _.extend( options.filters, {
            // all deleted, purged or not
            deleted : true,
            purged  : undefined
        });
        options.bypassCache = true;
        self.trigger( 'fetching-deleted', self );
        return self.fetchSection( section, options )
            .always( function(){ self.trigger( 'fetching-deleted-done', self ); });
    },

    fetchHiddenInSection : function( section, options ){
        options = options || {};
        var self = this;
        options.filters = _.extend( options.filters, {
            visible : false
        });
        options.bypassCache = true;
        self.trigger( 'fetching-deleted', self );
        return self.fetchSection( section, options )
            .always( function(){ self.trigger( 'fetching-deleted-done', self ); });
    },
});


//==============================================================================
    return {
        HistoryContents : HidSectionedHistoryContents
    };
});
