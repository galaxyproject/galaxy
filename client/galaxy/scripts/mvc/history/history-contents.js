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
// var _super = CONTROLLED_FETCH_COLLECTION.PaginatedCollection;
var _super = CONTROLLED_FETCH_COLLECTION.InfinitelyScrollingCollection;
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
    order : 'create_time',

    /** Set up */
    initialize : function( models, options ){
        options = options || {};
        this.historyId = options.historyId || null;

        // backbonejs uses collection.model.prototype.idAttribute to determine if a model is *already* in a collection
        //  and either merged or replaced. In this case, our 'model' is a function so we need to add idAttribute
        //  manually here - if we don't, contents will not merge but be replaced/swapped.
        this.model.prototype.idAttribute = 'type_id';

        /** @type {Boolean} does this collection contain and fetch deleted elements */
        this.includeDeleted = options.includeDeleted || false;
        /** @type {Boolean} does this collection contain and fetch non-visible elements */
        this.includeHidden = options.includeHidden || false;

        return _super.prototype.initialize.call( this, models, options );
    },

    /** root api url */
    urlRoot : Galaxy.root + 'api/histories',

    /** complete api url */
    url : function(){
        return this.urlRoot + '/' + this.historyId + '/contents';
    },

    // ........................................................................ common queries
    /** Get the id of every model in this collection not in a 'ready' state (running).
     *  @returns an array of model ids
     *  @see HistoryDatasetAssociation#inReadyState
     */
    running : function(){
        function filterFn( c ){ return !c.inReadyState(); }
        return new HistoryContents( this.filter( filterFn ) );
    },

    /** Get the model with the given hid
     *  @param {Int} hid the hid to search for
     *  @returns {HistoryDatasetAssociation} the model with the given hid or undefined if not found
     */
    getByHid : function( hid ){
        return _.first( this.filter( function( content ){ return content.get( 'hid' ) === hid; }) );
    },

    /** return true if all contents have details */
    haveDetails : function(){
        return this.all( function( content ){ return content.hasDetails(); });
    },

    // .................... hidden / deleted
    /** return a new contents collection of only hidden items */
    hidden : function(){
        function filterFn( c ){ return c.hidden(); }
        return new HistoryContents( this.filter( filterFn ) );
    },

    /** return a new contents collection of only hidden items */
    deleted : function(){
        function filterFn( c ){ return c.get( 'deleted' ); }
        return new HistoryContents( this.filter( filterFn ) );
    },

    /** return a new contents collection of only hidden items */
    visibleAndUndeleted : function(){
        function filterFn( c ){ return c.get( 'visible' ) && !c.get( 'deleted' ); }
        return new HistoryContents( this.filter( filterFn ) );
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
    /** using a queue, perform ajaxFn on each of the models in this collection */
    ajaxQueue : function( ajaxFn, options ){
        var queue = new AJAX_QUEUE.AjaxQueue( this.chain().reverse().map( function( content, i ){
            return function(){ return ajaxFn.call( content, options ); };
        }));
        queue.start();
        return queue.deferred;
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
    return {
        HistoryContents : HistoryContents
    };
});
