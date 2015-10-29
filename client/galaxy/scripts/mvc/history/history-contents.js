define([
    "mvc/history/history-content-model",
    "mvc/history/hda-model",
    "mvc/history/hdca-model",
    "mvc/base-mvc",
    "utils/localization"
], function( HISTORY_CONTENT, HDA_MODEL, HDCA_MODEL, BASE_MVC, _l ){
//==============================================================================
/** @class Backbone collection for history content.
 *      NOTE: history content seems like a dataset collection, but differs in that it is mixed:
 *          each element can be either an HDA (dataset) or a DatasetCollection and co-exist on
 *          the same level.
 *      Dataset collections on the other hand are not mixed and (so far) can only contain either
 *          HDAs or child dataset collections on one level.
 *      This is why this does not inherit from any of the DatasetCollections (currently).
 */
var HistoryContents = Backbone.Collection.extend( BASE_MVC.LoggableMixin ).extend(
/** @lends HistoryContents.prototype */{
//TODO:?? may want to inherit from some MixedModelCollection
//TODO:?? also consider inheriting from a 'DatasetList'
//TODO: can we decorate the mixed models using the model fn below (instead of having them build their own type_id)?

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    /** since history content is a mix, override model fn into a factory, creating based on history_content_type */
    model : function( attrs, options ) {
//TODO: can we move the type_id stuff here?
        //attrs.type_id = typeIdStr( attrs );

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

    /** Set up.
     *  @see Backbone.Collection#initialize
     */
    initialize : function( models, options ){
        options = options || {};
//TODO: could probably use the contents.history_id instead
        this.historyId = options.historyId;
        //this._setUpListeners();

        // backbonejs uses collection.model.prototype.idAttribute to determine if a model is *already* in a collection
        //  and either merged or replaced. In this case, our 'model' is a function so we need to add idAttribute
        //  manually here - if we don't, contents will not merge but be replaced/swapped.
        this.model.prototype.idAttribute = 'type_id';

        this.on( 'all', function(){
            this.debug( this + '.event:', arguments );
        });
    },

    /** root api url */
    urlRoot : galaxy_config.root + 'api/histories',
    /** complete api url */
    url : function(){
        return this.urlRoot + '/' + this.historyId + '/contents';
    },

    // ........................................................................ common queries
    /** Get the ids of every item in this collection
     *  @returns array of encoded ids
     */
    ids : function(){
//TODO: is this still useful since type_id
        return this.map( function( item ){ return item.get('id'); });
    },

    /** Get contents that are not ready
     *  @returns array of content models
     */
    notReady : function(){
        return this.filter( function( content ){
            return !content.inReadyState();
        });
    },

    /** Get the id of every model in this collection not in a 'ready' state (running).
     *  @returns an array of model ids
     *  @see HistoryDatasetAssociation#inReadyState
     */
    running : function(){
        var idList = [];
        this.each( function( item ){
            var isRunning = !item.inReadyState();
            if( isRunning ){
//TODO: is this still correct since type_id
                idList.push( item.get( 'id' ) );
            }
        });
        return idList;
    },

    /** Get the model with the given hid
     *  @param {Int} hid the hid to search for
     *  @returns {HistoryDatasetAssociation} the model with the given hid or undefined if not found
     */
    getByHid : function( hid ){
        return _.first( this.filter( function( content ){ return content.get( 'hid' ) === hid; }) );
    },

    //TODO:?? this may belong in the containing view
    /** Get every 'shown' model in this collection based on show_deleted/hidden
     *  @param {Boolean} show_deleted are we showing deleted content?
     *  @param {Boolean} show_hidden are we showing hidden content?
     *  @returns array of content models
     *  @see HistoryDatasetAssociation#isVisible
     */
    getVisible : function( show_deleted, show_hidden, filters ){
        filters = filters || [];
        //this.debug( 'filters:', filters );
        // always filter by show deleted/hidden first
        this.debug( 'checking isVisible' );
        var filteredHdas = new HistoryContents( this.filter( function( item ){
            return item.isVisible( show_deleted, show_hidden );
        }));

        _.each( filters, function( filterFn ){
            if( !_.isFunction( filterFn ) ){ return; }
            filteredHdas = new HistoryContents( filteredHdas.filter( filterFn ) );
        });
        return filteredHdas;
    },

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

    /** return true if any contents don't have details */
    haveDetails : function(){
        return this.all( function( content ){ return content.hasDetails(); });
    },

    // ........................................................................ ajax
    /** fetch detailed model data for all contents in this collection */
    fetchAllDetails : function( options ){
        options = options || {};
        var detailsFlag = { details: 'all' };
        options.data = ( options.data )?( _.extend( options.data, detailsFlag ) ):( detailsFlag );
        return this.fetch( options );
    },

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

    // ........................................................................ sorting/filtering
    /** return a new collection of contents whose attributes contain the substring matchesWhat */
    matches : function( matchesWhat ){
        return this.filter( function( content ){
            return content.matches( matchesWhat );
        });
    },

    // ........................................................................ misc
    /** override to ensure type id is set */
    set : function( models, options ){
        models = _.isArray( models )? models : [ models ];
        _.each( models, function( model ){
            if( !model.type_id || !model.get || !model.get( 'type_id' ) ){
                model.type_id = HISTORY_CONTENT.typeIdStr( model.history_content_type, model.id );
            }
        });
        Backbone.Collection.prototype.set.call( this, models, options );
    },

    /** */
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


    /** In this override, copy the historyId to the clone */
    clone : function(){
        var clone = Backbone.Collection.prototype.clone.call( this );
        clone.historyId = this.historyId;
        return clone;
    },

    /** debugging */
    print : function(){
        var contents = this;
        contents.each( function( c ){
            contents.debug( c );
            if( c.elements ){
                contents.debug( '\t elements:', c.elements );
            }
        });
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
