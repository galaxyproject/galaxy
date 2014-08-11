define([
    "mvc/dataset/states",
    "mvc/history/history-content-base",
    "utils/localization"
], function( STATES, HISTORY_CONTENT, _l ){
//==============================================================================
var _super = HISTORY_CONTENT.HistoryContent;
/** @class (HDA) model for a Galaxy dataset
 *      related to a history.
 *  @name HistoryDatasetAssociation
 *
 *  @augments HistoryContent
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HistoryDatasetAssociation = _super.extend(
/** @lends HistoryDatasetAssociation.prototype */{
    
    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    //logger              : console,
    
    /** default attributes for a model */
    defaults : _.extend( _.clone( _super.prototype.defaults ), {
        // ---these are part of an HDA proper:

        // often used with tagging
        model_class         : 'HistoryDatasetAssociation',
        history_content_type : 'dataset',
        
//TODO: these are dataset related and should be moved to some more basal dataset class
        // sniffed datatype (sam, tabular, bed, etc.)
        data_type           : '',
        // size in bytes
        file_size           : 0,
        file_ext            : '',

        // array of associated file types (eg. [ 'bam_index', ... ])
        meta_files          : [],

        misc_blurb          : '',
        misc_info           : '',

        tags                : []
        // do NOT default on annotation, as this default is valid and will be passed on 'save'
        //  which is incorrect behavior when the model is only partially fetched (annos are not passed in summary data)
        //annotation          : ''
    }),

    /** Set up the model, determine if accessible, bind listeners
     *  @see Backbone.Model#initialize
     */
    initialize : function( attributes, options ){
        this.log( this + '.initialize', this.attributes );
        this.log( '\tparent history_id: ' + this.get( 'history_id' ) );

        //!! this state is not in trans.app.model.Dataset.states - set it here -
        if( !this.get( 'accessible' ) ){
            this.set( 'state', STATES.NOT_VIEWABLE );
        }

        _super.prototype.initialize.call( this, attributes, options );
    },

    /** set up any event listeners
     *  event: state:ready  fired when this HDA moves into a ready state
     */
    _setUpListeners : function(){
        // if the state has changed and the new state is a ready state, fire an event
        this.on( 'change:state', function( currModel, newState ){
            this.log( this + ' has changed state:', currModel, newState );
            if( this.inReadyState() ){
                this.trigger( 'state:ready', currModel, newState, this.previous( 'state' ) );
            }
        });
    },

    // ........................................................................ common queries
    /** Does this model already contain detailed data (as opposed to just summary level data)? */
    hasDetails : function(){
        //?? this may not be reliable
        return _.has( this.attributes, 'genome_build' );
    },

    /** Convenience function to match hda.has_data. */
    hasData : function(){
        return ( this.get( 'file_size' ) > 0 );
    },

    // ........................................................................ ajax
    /** controller urls assoc. with this HDA */
    urls : function(){
        var parentUrls = _super.prototype.urls.call( this );
            id = this.get( 'id' );
        if( !id ){ return parentUrls; }
        var urls = {
            'purge'         : galaxy_config.root + 'datasets/' + id + '/purge_async',

            'display'       : galaxy_config.root + 'datasets/' + id + '/display/?preview=True',
            'edit'          : galaxy_config.root + 'datasets/' + id + '/edit',

            'download'      : galaxy_config.root + 'datasets/' + id + '/display?to_ext=' + this.get( 'file_ext' ),
            'report_error'  : galaxy_config.root + 'dataset/errors?id=' + id,
            'rerun'         : galaxy_config.root + 'tool_runner/rerun?id=' + id,
            'show_params'   : galaxy_config.root + 'datasets/' + id + '/show_params',
            'visualization' : galaxy_config.root + 'visualization',

            'annotation': { 'get': galaxy_config.root + 'dataset/get_annotation_async?id=' + id,
                            'set': galaxy_config.root + 'dataset/annotate_async?id=' + id },
            'meta_download' : galaxy_config.root + 'dataset/get_metadata_file?hda_id=' + id + '&metadata_name='
        };
        return _.extend( parentUrls, urls );
    },

    /** purge this HDA and remove the underlying dataset file from the server's fs */
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
        //    console.debug( 'response', response );
        //    //hda.set({ deleted: true, purged: true });
        //    hda.set( response );
        //});
        //return xhr;

        options.url = galaxy_config.root + 'datasets/' + this.get( 'id' ) + '/purge_async';

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

    // ........................................................................ search
    /** what attributes of an HDA will be used in a text search */
    searchAttributes : _super.prototype.searchAttributes.concat([
        'file_ext', 'genome_build', 'misc_blurb', 'misc_info', 'annotation', 'tags'
    ]),

    /** our attr keys don't often match the labels we display to the user - so, when using
     *      attribute specifiers ('name="bler"') in a term, allow passing in aliases for the
     *      following attr keys.
     */
    searchAliases : _.extend( _.clone( _super.prototype.searchAliases ), {
        format      : 'file_ext',
        database    : 'genome_build',
        blurb       : 'misc_blurb',
        description : 'misc_blurb',
        info        : 'misc_info',
        tag         : 'tags'
    }),

    // ........................................................................ misc
    /** String representation */
    toString : function(){
        var nameAndId = this.get( 'id' ) || '';
        if( this.get( 'name' ) ){
            nameAndId = this.get( 'hid' ) + ' :"' + this.get( 'name' ) + '",' + nameAndId;
        }
        return 'HDA(' + nameAndId + ')';
    }
});


//==============================================================================
    return {
        HistoryDatasetAssociation   : HistoryDatasetAssociation
    };
});
