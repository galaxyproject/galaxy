//define([
//    "../mvc/base-mvc"
//], function(){
//==============================================================================
/**
 *
 */
var History = BaseModel.extend( LoggableMixin ).extend({
    //TODO: bind change events from items and collection to this (itemLengths, states)

    // uncomment this out see log messages
    //logger              : console,

    // values from api (may need more)
    defaults : {
        id              : '',
        name            : '',
        state           : '',

        diskSize : 0,
        deleted : false,

        //tags        : [],
        annotation  : null,

        //TODO: message? how to get over the api?
        message     : null
    },

    url : function(){
        // api location of history resource
        //TODO: hardcoded
        return 'api/histories/' + this.get( 'id' );
    },

    initialize : function( initialSettings, initialHdas ){
        this.log( this + ".initialize:", initialSettings, initialHdas );

        this.hdas = new HDACollection();

        // if we've got hdas passed in the constructor, load them and set up updates if needed
        if( initialHdas && initialHdas.length ){
            this.hdas.reset( initialHdas );
            this.checkForUpdates();
        }

        //this.on( 'change', function( currModel, changedList ){
        //    this.log( this + ' has changed:', currModel, changedList );
        //});
        //this.bind( 'all', function( event ){
        //    //this.log( this + '', arguments );
        //    console.info( this + '', arguments );
        //});
    },

    // get data via the api (alternative to sending options,hdas to initialize)
    //TODO: this needs work - move to more straightforward deferred
    // events: loaded, loaded:user, loaded:hdas
    loadFromApi : function( historyId, success ){
        var history = this;

        // fetch the history AND the user (mainly to see if they're logged in at this point)
        history.attributes.id = historyId;
        //TODO:?? really? fetch user here?
        jQuery.when(
                jQuery.ajax( 'api/users/current' ),
                history.fetch()

            ).then( function( userResponse, historyResponse ){
                //console.warn( 'fetched user: ', userResponse[0] );
                //console.warn( 'fetched history: ', historyResponse[0] );
                history.attributes.user = userResponse[0]; //? meh.

                history.trigger( 'loaded:user', userResponse[0] );
                history.trigger( 'loaded', historyResponse[0] );

            }).then( function(){
                // ...then the hdas (using contents?ids=...)
                jQuery.ajax( history.url() + '/contents?' + jQuery.param({
                    ids : history.hdaIdsFromStateIds().join( ',' )

                // reset the collection to the hdas returned
                })).success( function( hdas ){
                    //console.warn( 'fetched hdas', hdas );
                    history.hdas.reset( hdas );
                    history.checkForUpdates();

                    history.trigger( 'loaded:hdas', hdas );
                    if( success ){ callback( history ); }
                });
            });
    },

    // reduce the state_ids map of hda id lists -> a single list of ids
    //...ugh - seems roundabout; necessary because the history doesn't have a straightforward list of ids
    //  (and history_contents/index curr returns a summary only)
    hdaIdsFromStateIds : function(){
        return _.reduce( _.values( this.get( 'state_ids' ) ), function( reduction, currIdList ){
            return reduction.concat( currIdList );
        });
    },

    // get the history's state from it's cummulative ds states, delay + update if needed
    // events: ready
    checkForUpdates : function( datasets ){
        // get overall History state from collection, run updater if History has running/queued hdas
        // boiling it down on the client to running/not
        if( this.hdas.running().length ){
            this.stateUpdater();

        } else {
            this.trigger( 'ready' );
        }
        return this;
    },

    // update this history, find any hda's running/queued, update ONLY those that have changed states,
    //  set up to run this again in some interval of time
    // events: ready
    stateUpdater : function(){
        var history = this,
            oldState = this.get( 'state' ),
            // state ids is a map of every possible hda state, each containing a list of ids for hdas in that state
            oldStateIds = this.get( 'state_ids' );

        // pull from the history api
        //TODO: fetch?
        jQuery.ajax( 'api/histories/' + this.get( 'id' )

        ).success( function( response ){
            //this.log( 'historyApiRequest, response:', response );
            history.set( response );
            history.log( 'current history state:', history.get( 'state' ),
                '(was)', oldState,
                'new size:', history.get( 'nice_size' ) );

            //TODO: revisit this - seems too elaborate, need something straightforward
            // for each state, check for the difference between old dataset states and new
            //  the goal here is to check ONLY those datasets that have changed states (not all datasets)
            var changedIds = [];
            _.each( _.keys( response.state_ids ), function( state ){
                var diffIds = _.difference( response.state_ids[ state ], oldStateIds[ state ] );
                // aggregate those changed ids
                changedIds = changedIds.concat( diffIds );
            });

            // send the changed ids (if any) to dataset collection to have them fetch their own model changes
            if( changedIds.length ){
                history.hdas.update( changedIds );
            }

            // set up to keep pulling if this history in run/queue state
            //TODO: magic number here
            if( ( history.get( 'state' ) === HistoryDatasetAssociation.STATES.RUNNING )
            ||  ( history.get( 'state' ) === HistoryDatasetAssociation.STATES.QUEUED ) ){
                setTimeout( function(){
                    history.stateUpdater();
                }, 4000 );

            // otherwise, we're now in a 'ready' state (no hdas running)
            } else {
                history.trigger( 'ready' );
            }

        }).error( function( xhr, status, error ){
            if( console && console.warn ){
                console.warn( 'Error getting history updates from the server:', xhr, status, error );
            }
            alert( _l( 'Error getting history updates from the server.' ) + '\n' + error );
        });
    },

    toString : function(){
        var nameString = ( this.get( 'name' ) )?
            ( ',' + this.get( 'name' ) ) : ( '' );
        return 'History(' + this.get( 'id' ) + nameString + ')';
    }
});

//==============================================================================
/** A collection of histories (per user or admin)
 *      (stub) currently unused
 */
var HistoryCollection = Backbone.Collection.extend( LoggableMixin ).extend({
    model   : History,
    urlRoot : 'api/histories',
    //logger  : console
});

//==============================================================================
//return {
//    History           : History,
//    HistoryCollection : HistoryCollection,
//};});
