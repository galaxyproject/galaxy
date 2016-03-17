define([
    "mvc/history/history-content-model",
    "mvc/base/controlled-fetch-collection",
    "mvc/history/hda-model",
    "mvc/history/hdca-model",
    "mvc/history/history-preferences",
    "mvc/base-mvc"
], function( HISTORY_CONTENT, CONTROLLED_FETCH_COLLECTION, HDA_MODEL, HDCA_MODEL, HISTORY_PREFS, BASE_MVC ){
'use strict';

//==============================================================================
var _super = CONTROLLED_FETCH_COLLECTION.ControlledFetchCollection;
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
    },

    /** root api url */
    urlRoot : Galaxy.root + 'api/histories',

    /** complete api url */
    url : function(){
        return this.urlRoot + '/' + this.historyId + '/contents';
    },

    // ........................................................................ order
    /** @type {String} order used here and when fetching from server */
    order : 'create_time',

//TODO: generalize
    /** local comparator */
    comparator : function _create_timeDsc( a, b ){
        var createTimeA = a.get( 'create_time' );
        var createTimeB = b.get( 'create_time' );
        // console.log( 'comparator', createTimeA, createTimeB );
        if( createTimeA > createTimeB ){ return  1; }
        if( createTimeA < createTimeB ){ return  -1; }
        return 0;
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

    /** return true if any contents don't have details */
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

//TODO: revisit includeDeleted/Hidden naming and toggle fn
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
// TODO: here?
            var expandedIds = HISTORY_PREFS.HistoryPrefs.get( this.historyId ).get( 'expandedIds' );
            options.details = _.values( expandedIds ).join( ',' );
        }
        return _super.prototype.fetch.call( this, options );
    },

    // ............. ControlledFetch stuff
    /** override to filter requested contents to those updated after the Date 'since' */
    fetchUpdated : function( since, options ){
        if( since ){
            options = options || { filters: {} };
            options.filters = {
                'update_time-ge' : since.toISOString()
            };
        }
        console.log( 'fetching updated:', this.historyId );
        return this.fetch( options );
    },

    /**  */
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

    /**  */
    _buildFetchFilters : function( options ){
        var filters = {};
        if( !this.includeDeleted ){
            filters.deleted = false;
            filters.purged = false;
        }
        if( !this.includeHidden ){
            filters.visible = true;
        }
        return _.defaults( _super.prototype._buildFetchFilters( this, options ), filters );
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
        var deferred = jQuery.Deferred(),
            startingLength = this.length,
            responses = [];

        if( !startingLength ){
            deferred.resolve([]);
            return deferred;
        }

        // use reverse order (stylistic choice)
        var ajaxFns = this.chain().reverse().map( function( content, i ){
            return function(){
                var xhr = ajaxFn.call( content, options );
                // if successful, notify using the deferred to allow tracking progress
                xhr.done( function( response ){
                    deferred.notify({ curr: i, total: startingLength, response: response, model: content });
                });
                // (regardless of previous error or success) if not last ajax call, shift and call the next
                //  if last fn, resolve deferred
                xhr.always( function( response ){
                    responses.push( response );
                    if( ajaxFns.length ){
                        ajaxFns.shift()();
                    } else {
                        deferred.resolve( responses );
                    }
                });
            };
        }).value();
        // start the queue
        ajaxFns.shift()();

        return deferred;
    },

    /**  */
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
                type    : type
            })
            .done( function( response ){
                collection.add([ response ]);
            })
            .fail( function( error, status, message ){
                collection.trigger( 'error', collection, xhr, {},
                    'Error copying contents', { type: type, id: id, source: contentType });
            });
        return xhr;
    },

    /**  */
    createHDCA : function( elementIdentifiers, collectionType, name, options ){
        //precondition: elementIdentifiers is an array of plain js objects
        //  in the proper form to create the collectionType
        var contents = this,
            typeToModel = {
                list    : HDCA_MODEL.HistoryListDatasetCollection,
                paired  : HDCA_MODEL.HistoryPairDatasetCollection
            },
            hdca = new (typeToModel[ collectionType ])({
                history_id          : this.historyId,
                name                : name,
                // should probably be able to just send in a bunch of json here and restruct per class
                element_identifiers : elementIdentifiers
            });
        // do I even need to use new above, can I just pass the attrs here
        return hdca.save()
            .done( function( response ){
                contents.add( hdca );
            })
            .fail( function( xhr, status, message ){
                contents.trigger( 'error', xhr, status, message );
            });
    },

    // ........................................................................ searching
    /** return a new collection of contents whose attributes contain the substring matchesWhat */
    matches : function( matchesWhat ){
        return this.filter( function( content ){
            return content.matches( matchesWhat );
        });
    },

    // ........................................................................ misc
    /** override to ensure type id is set */
//TODO: needed now?
    set : function( models, options ){
        models = _.isArray( models )? models : [ models ];
        _.each( models, function( model ){
            if( !model.type_id || !model.get || !model.get( 'type_id' ) ){
                model.type_id = HISTORY_CONTENT.typeIdStr( model.history_content_type, model.id );
            }
        });
        Backbone.Collection.prototype.set.call( this, models, options );
    },

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
window.HistoryContents = HistoryContents;

//==============================================================================
    return {
        HistoryContents : HistoryContents
    };
});
