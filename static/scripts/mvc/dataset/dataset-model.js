define([
    "mvc/dataset/states",
    "mvc/base-mvc",
    "utils/localization"
], function( STATES, BASE_MVC, _l ){
//==============================================================================
var searchableMixin = BASE_MVC.SearchableModelMixin;
/** @class base model for any DatasetAssociation (HDAs, LDDAs, DatasetCollectionDAs).
 *      No knowledge of what type (HDA/LDDA/DCDA) should be needed here.
 *  The DA's are made searchable (by attribute) by mixing in SearchableModelMixin.
 */
var DatasetAssociation = Backbone.Model.extend( BASE_MVC.LoggableMixin ).extend(
        BASE_MVC.mixin( searchableMixin, /** @lends DatasetAssociation.prototype */{

    /** default attributes for a model */
    defaults : {
        state               : STATES.NEW,
        deleted             : false,
        purged              : false,

        // unreliable attribute
        name                : '(unnamed dataset)',

//TODO: update to false when this is correctly passed from the API (when we have a security model for this)
        accessible          : true,

        // sniffed datatype (sam, tabular, bed, etc.)
        data_type           : '',
        file_ext            : '',

        // size in bytes
        file_size           : 0,

        // array of associated file types (eg. [ 'bam_index', ... ])
        meta_files          : [],

        misc_blurb          : '',
        misc_info           : '',

        tags                : []
        // do NOT default on annotation, as this default is valid and will be passed on 'save'
        //  which is incorrect behavior when the model is only partially fetched (annos are not passed in summary data)
        //annotation          : ''
    },

    /** instance vars and listeners */
    initialize : function( attributes, options ){
        this.debug( this + '(Dataset).initialize', attributes, options );

        //!! this state is not in trans.app.model.Dataset.states - set it here -
        if( !this.get( 'accessible' ) ){
            this.set( 'state', STATES.NOT_VIEWABLE );
        }

        /** Datasets rely/use some web controllers - have the model generate those URLs on startup */
        this.urls = this._generateUrls();

        this._setUpListeners();
    },
    
    /** returns misc. web urls for rendering things like re-run, display, etc. */
    _generateUrls : function(){
//TODO: would be nice if the API did this
        var id = this.get( 'id' );
        if( !id ){ return {}; }
        var urls = {
            'purge'         : 'datasets/' + id + '/purge_async',
            'display'       : 'datasets/' + id + '/display/?preview=True',
            'edit'          : 'datasets/' + id + '/edit',
            'download'      : 'datasets/' + id + '/display?to_ext=' + this.get( 'file_ext' ),
            'report_error'  : 'dataset/errors?id=' + id,
            'rerun'         : 'tool_runner/rerun?id=' + id,
            'show_params'   : 'datasets/' + id + '/show_params',
            'visualization' : 'visualization',
            'meta_download' : 'dataset/get_metadata_file?hda_id=' + id + '&metadata_name='
        };
//TODO: global
        var root = ( window.galaxy_config && galaxy_config.root )?( galaxy_config.root ):( '/' );
        _.each( urls, function( value, key ){
            urls[ key ] = root + value;
        });
        this.urls = urls;
        return urls;
    },

    /** set up any event listeners
     *  event: state:ready  fired when this DA moves into/is already in a ready state
     */
    _setUpListeners : function(){
        // if the state has changed and the new state is a ready state, fire an event
        this.on( 'change:state', function( currModel, newState ){
            this.log( this + ' has changed state:', currModel, newState );
            if( this.inReadyState() ){
                this.trigger( 'state:ready', currModel, newState, this.previous( 'state' ) );
            }
        });
        this.on( 'change:urls', function(){
            console.warn( 'change:urls', arguments );
        });
        // the download url (currenlty) relies on having a correct file extension
        this.on( 'change:id change:file_ext', function( currModel ){
            this._generateUrls();
        });
    },

    // ........................................................................ common queries
    /** override to add urls */
    toJSON : function(){
        var json = Backbone.Model.prototype.toJSON.call( this );
        //console.warn( 'returning json?' );
        //return json;
        return _.extend( json, {
            urls : this.urls
        });
    },

    /** Is this dataset deleted or purged? */
    isDeletedOrPurged : function(){
        return ( this.get( 'deleted' ) || this.get( 'purged' ) );
    },

    /** Is this dataset in a 'ready' state; where 'Ready' states are states where no
     *      processing (for the ds) is left to do on the server.
     */
    inReadyState : function(){
        var ready = _.contains( STATES.READY_STATES, this.get( 'state' ) );
        return ( this.isDeletedOrPurged() || ready );
    },

    /** Does this model already contain detailed data (as opposed to just summary level data)? */
    hasDetails : function(){
        //?? this may not be reliable
        return _.has( this.attributes, 'genome_build' );
    },

    /** Convenience function to match dataset.has_data. */
    hasData : function(){
        return ( this.get( 'file_size' ) > 0 );
    },

    // ........................................................................ ajax
    //NOTE: subclasses of DA's will need to implement url and urlRoot in order to have these work properly

    /** save this dataset, _Mark_ing it as deleted (just a flag) */
    'delete' : function( options ){
        if( this.get( 'deleted' ) ){ return jQuery.when(); }
        return this.save( { deleted: true }, options );
    },
    /** save this dataset, _Mark_ing it as undeleted */
    undelete : function( options ){
        if( !this.get( 'deleted' ) || this.get( 'purged' ) ){ return jQuery.when(); }
        return this.save( { deleted: false }, options );
    },

    /** remove the file behind this dataset from the filesystem (if permitted) */
    purge : function _purge( options ){
//TODO: use, override model.destroy, HDA.delete({ purge: true })
        if( this.get( 'purged' ) ){ return jQuery.when(); }
        options = options || {};
        //var hda = this,
        //    //xhr = jQuery.ajax( this.url() + '?' + jQuery.param({ purge: true }), _.extend({
        //    xhr = jQuery.ajax( this.url(), _.extend({
        //        type : 'DELETE',
        //        data : {
        //            purge : true
        //        }
        //    }, options ));
        //
        //xhr.done( function( response ){
        //    hda.debug( 'response', response );
        //    //hda.set({ deleted: true, purged: true });
        //    hda.set( response );
        //});
        //return xhr;

        options.url = this.urls.purge;

        //TODO: ideally this would be a DELETE call to the api
        //  using purge async for now
        var hda = this,
            xhr = jQuery.ajax( options );
        xhr.done( function( message, status, responseObj ){
            hda.set({ deleted: true, purged: true });
        });
        xhr.fail( function( xhr, status, message ){
            // Exception messages are hidden within error page including:  '...not allowed in this Galaxy instance.'
            // unbury and re-add to xhr
            var error = _l( "Unable to purge dataset" );
            var messageBuriedInUnfortunatelyFormattedError = ( 'Removal of datasets by users '
                + 'is not allowed in this Galaxy instance' );
            if( xhr.responseJSON && xhr.responseJSON.error ){
                error = xhr.responseJSON.error;
            } else if( xhr.responseText.indexOf( messageBuriedInUnfortunatelyFormattedError ) !== -1 ){
                error = messageBuriedInUnfortunatelyFormattedError;
            }
            xhr.responseText = error;
            hda.trigger( 'error', hda, xhr, options, _l( error ), { error: error } );
        });
        return xhr;
    },

    // ........................................................................ searching
    // see base-mvc, SearchableModelMixin

    /** what attributes of an HDA will be used in a text search */
    searchAttributes : [
        'name', 'file_ext', 'genome_build', 'misc_blurb', 'misc_info', 'annotation', 'tags'
    ],

    /** our attr keys don't often match the labels we display to the user - so, when using
     *      attribute specifiers ('name="bler"') in a term, allow passing in aliases for the
     *      following attr keys.
     */
    searchAliases : {
        title       : 'name',
        format      : 'file_ext',
        database    : 'genome_build',
        blurb       : 'misc_blurb',
        description : 'misc_blurb',
        info        : 'misc_info',
        tag         : 'tags'
    },

    // ........................................................................ misc
    /** String representation */
    toString : function(){
        var nameAndId = this.get( 'id' ) || '';
        if( this.get( 'name' ) ){
            nameAndId = '"' + this.get( 'name' ) + '",' + nameAndId;
        }
        return 'Dataset(' + nameAndId + ')';
    }
}));


//==============================================================================
/** @class Backbone collection for dataset associations.
 */
var DatasetAssociationCollection = Backbone.Collection.extend( BASE_MVC.LoggableMixin ).extend(
/** @lends HistoryContents.prototype */{
    model : DatasetAssociation,

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    /** root api url */
    urlRoot : (( window.galaxy_config && galaxy_config.root )?( galaxy_config.root ):( '/' ))
        + 'api/datasets',

    // ........................................................................ common queries
    /** Get the ids of every item in this collection
     *  @returns array of encoded ids
     */
    ids : function(){
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

//    /** Get the id of every model in this collection not in a 'ready' state (running).
//     *  @returns an array of model ids
//     */
//    running : function(){
//        var idList = [];
//        this.each( function( item ){
//            var isRunning = !item.inReadyState();
//            if( isRunning ){
////TODO: is this still correct since type_id
//                idList.push( item.get( 'id' ) );
//            }
//        });
//        return idList;
//    },

    /** return true if any datasets don't have details */
    haveDetails : function(){
        return this.all( function( dataset ){ return dataset.hasDetails(); });
    },

    // ........................................................................ ajax
    ///** fetch detailed model data for all datasets in this collection */
    //fetchAllDetails : function( options ){
    //    options = options || {};
    //    var detailsFlag = { details: 'all' };
    //    options.data = ( options.data )?( _.extend( options.data, detailsFlag ) ):( detailsFlag );
    //    return this.fetch( options );
    //},

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
        var ajaxFns = this.chain().reverse().map( function( dataset, i ){
            return function(){
                var xhr = ajaxFn.call( dataset, options );
                // if successful, notify using the deferred to allow tracking progress
                xhr.done( function( response ){
                    deferred.notify({ curr: i, total: startingLength, response: response, model: dataset });
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

    // ........................................................................ sorting/filtering
    /** return a new collection of datasets whose attributes contain the substring matchesWhat */
    matches : function( matchesWhat ){
        return this.filter( function( dataset ){
            return dataset.matches( matchesWhat );
        });
    },

    // ........................................................................ misc
    /** override to get a correct/smarter merge when incoming data is partial */
    set : function( models, options ){
        // arrrrrrrrrrrrrrrrrg...
        //  (e.g. stupid backbone)
        //  w/o this partial models from the server will fill in missing data with model defaults
        //  and overwrite existing data on the client
        // see Backbone.Collection.set and _prepareModel
        var collection = this;
        models = _.map( models, function( model ){
            if( !collection.get( model.id ) ){ return model; }

            // merge the models _BEFORE_ calling the superclass version
            var merged = existing.toJSON();
            _.extend( merged, model );
            return merged;
        });
        // now call superclass when the data is filled
        Backbone.Collection.prototype.set.call( this, models, options );
    },

//    /** Convert this ad-hoc collection of hdas to a formal collection tracked
//        by the server.
//    **/
//    promoteToHistoryDatasetCollection : function _promote( history, collection_type, options ){
////TODO: seems like this would be better in mvc/collections
//        options = options || {};
//        options.url = this.url();
//        options.type = "POST";
//        var full_collection_type = collection_type;
//        var element_identifiers = [],
//            name = null;
//
//        // This mechanism is rough - no error handling, allows invalid selections, no way
//        // for user to pick/override element identifiers. This is only really meant
//        if( collection_type === "list" ) {
//            this.chain().each( function( hda ) {
//                // TODO: Handle duplicate names.
//                var name = hda.attributes.name;
//                var id = hda.get('id');
//                var content_type = hda.attributes.history_content_type;
//                if( content_type === "dataset" ) {
//                    if( full_collection_type !== "list" ) {
//                        this.log( "Invalid collection type" );
//                    }
//                    element_identifiers.push( { name: name, src: "hda", id: id } );
//                } else {
//                    if( full_collection_type === "list" ) {
//                        full_collection_type = "list:" + hda.attributes.collection_type;
//                    } else {
//                        if( full_collection_type !== "list:" + hda.attributes.collection_type ) {
//                            this.log( "Invalid collection type" );
//                        }
//                    }
//                    element_identifiers.push( { name: name, src: "hdca", id: id } );
//                }
//            });
//            name = "New Dataset List";
//        } else if( collection_type === "paired" ) {
//            var ids = this.ids();
//            if( ids.length !== 2 ){
//                // TODO: Do something...
//            }
//            element_identifiers.push( { name: "forward", src: "hda", id: ids[ 0 ] } );
//            element_identifiers.push( { name: "reverse", src: "hda", id: ids[ 1 ] } );
//            name = "New Dataset Pair";
//        }
//        options.data = {
//            type: "dataset_collection",
//            name: name,
//            collection_type: full_collection_type,
//            element_identifiers: JSON.stringify( element_identifiers )
//        };
//
//        var xhr = jQuery.ajax( options );
//        xhr.done( function( message, status, responseObj ){
//            history.refresh( );
//        });
//        xhr.fail( function( xhr, status, message ){
//            if( xhr.responseJSON && xhr.responseJSON.error ){
//                error = xhr.responseJSON.error;
//            } else {
//                error = xhr.responseJSON;
//            }
//            xhr.responseText = error;
//            // Do something?
//        });
//        return xhr;
//    },

    /** String representation. */
    toString : function(){
         return ([ 'DatasetAssociationCollection(', this.length, ')' ].join( '' ));
    }
});


//==============================================================================
    return {
        DatasetAssociation              : DatasetAssociation,
        DatasetAssociationCollection    : DatasetAssociationCollection
    };
});
