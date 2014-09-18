//==============================================================================
/*
TODO:
    ?? superclass dataloader, subclass lazydataloader??

*/
//==============================================================================
/**
 *  Object to progressively load JSON data from a REST url, delaying some time between loading chunks
 *
 *  Will load size amount of data every delay ms, starting at start and ending at total.
 *
 *  NOTE: Data from ajax loading is aggregated in a list, with one element for each ajax response.
 *      It's up to the calling code to combine the results in a meaningful, correct way.
 *
 *  example:
 *  var loader = new scatterplot.LazyDataLoader({
 *      //logger  : console,
 *      url     : ( apiDatasetsURL + '/' + hda.id + '?data_type=raw_data'
 *                + '&columns=[10,14]' ),
 *      total   : hda.metadata_data_lines,
 *      size    : 500,
 *
 *      initialize : function( config ){
 *          // ... do some stuff
 *      },
 *
 *      buildUrl : function( start, size ){
 *          // change the formation of start, size in query string
 *          return loader.url + '&' + jQuery.param({
 *              start_val: start,
 *              max_vals:  size
 *          });
 *      },
 *  });
 *
 *  // you can use events
 *  $( loader ).bind( 'error', function( event, xhr, status, error ){
 *      alert( loader + ' ERROR:' + status + '\n' + error );
 *      // bail out...
 *  });
 *  $( loader ).bind( 'loaded.new', function( event, response ){
 *      console.info( 'new data available:', event, response );
 *      // ... do stuff with new data
 *  });
 *  $( loader ).bind( 'complete', function( event, allDataArray, total ){
 *      console.info( 'final load complete:', event, allDataArray, total );
 *      // ... do stuff with all data
 *  });
 *
 *  // ...or use a callback called when all data is loaded
 *  loader.load( function( dataArray ){ console.debug( 'FINISHED!', x, y, z ); } );
 */
function LazyDataLoader( config ){
    // for now assume:
    //  get, async, and params sent via url query string
    //  we want json
    //  we know the size of the data on the server beforehand
    var loader = this,
        // events to trigger when new or all data has been loaded
        //  new batches of data (including last). Will be sent: the ajax response data, start value, and size
        LOADED_NEW_EVENT  = 'loaded.new',
        //  all data has been loaded: the final loader's data array and the total
        LOADED_ALL_EVENT  = 'complete';
        //  error from ajax
        ERROR_EVENT       = 'error';

    jQuery.extend( loader, LoggableMixin );
    jQuery.extend( loader, {

        //NOTE: the next two need to be sent in config (required)
        // total size of data on server
        total   : undefined,
        // url of service to get the data
        url     : undefined,

        // holds the interval id for the current load delay
        currentIntervalId   : undefined,

        // each load call will add an element to this array
        //  it's the responsibility of the code using this to combine them properly
        data    : [],
        // ms btwn recursive loads
        delay   : 4000,
        // starting line, element, whatever
        start   : 0,
        // size to fetch per load
        size    : 4000,

        // loader init func: extends loader with config and calls config.init if there
        //@param {object} config : object containing variables to override (or additional)
        initialize : function( config ){
            jQuery.extend( loader, config );

            // call the custom initialize function if any
            //  only dangerous if the user tries LazyDataLoader.prototype.init
            if( config.hasOwnProperty( 'initialize' ) ){
                config.initialize.call( loader, config );
            }
            this.log( this + ' initialized:', loader );
        },

        // returns query string formatted start and size (for the next fetch) appended to the loader.url
        //OVERRIDE: to change how params are passed, param names, etc.
        //@param {int} start : the line/row/datum indicating where in the dataset the next load begins
        //@param {int} size : the number of lines/rows/data to get on the next load
        buildUrl : function( start, size ){
            // currently VERY SPECIFIC to using data_providers.py start_val, max_vals params
            return this.url + '&' + jQuery.param({
                start_val: start,
                max_vals:  size
            });
        },

        //OVERRIDE: to handle ajax errors differently
        ajaxErrorFn : function( xhr, status, error ){
            console.error( 'ERROR fetching data:', error );
        },

        // converters passed to the jQuery ajax call for data type parsing
        //OVERRIDE: to provide custom parsing
        converters : {
            '* text'    : window.String,
            'text html' : true,
            'text xml'  : jQuery.parseXML,
            'text json' : jQuery.parseJSON
        },

        // interface to begin load (and first recursive call)
        //@param {Function} callback : function to execute when all data is loaded. callback is passed loader.data
        load : function( callback ){
            this.log( this + '.load' );

            // ensure necessary stuff
            if( !loader.url ){ throw( loader + ' requires a url' ); }

            if( this.total === null ){
                this.log( '\t total is null (will load all)' );
            } else {
                this.log( '\t total:', this.total );
            }
            //if( !loader.total ){ throw( loader + ' requires a total (total size of the data)' ); }

            //FIRST RECURSION: start
            var startingSize = loader.size;
            if( ( loader.total !== null ) && ( loader.total < loader.size ) ){
                startingSize = loader.total;
            }
            loader.log( loader + '\t beginning recursion' );
            loadHelper( loader.start, startingSize );

            //FIRST, SUBSEQUENT RECURSION function
            function loadHelper( start, size ){
                loader.log( loader + '.loadHelper, start:', start, 'size:', size );
                var url = loader.buildUrl( start, size );
                loader.log( '\t url:', url );

                jQuery.ajax({
                    url         : loader.buildUrl( start, size ),
                    converters  : loader.converters,
                    dataType    : 'json',

                    error       : function( xhr, status, error ){
                        loader.log( '\t ajax error, status:', status, 'error:', error );
                        if( loader.currentIntervalId ){
                            clearInterval( loader.currentIntervalId );
                        }
                        $( loader ).trigger( ERROR_EVENT, [ status, error ] );
                        loader.ajaxErrorFn( xhr, status, error );
                    },

                    success     : function( response ){
                        loader.log( '\t ajax success, response:', response, 'next:', next, 'remainder:', remainder );

                        if( response !== null ){
                            // store the response as is in a new element
                            //TODO:?? store start, size as well?
                            loader.data.push( response );

                            //TODO: these might not be the best way to split this up
                            // fire the first load event (if this is the first batch) AND partial
                            $( loader ).trigger( LOADED_NEW_EVENT, [ response, start, size ] );

                            //RECURSION:
                            var next = start + size,
                                remainder = loader.size;

                            if( loader.total !== null ){
                                remainder = Math.min( loader.total - next, loader.size );
                            }
                            loader.log( '\t next recursion, start:', next, 'size:', remainder );

                            // if we haven't gotten everything yet, so set up for next recursive call and set the timer
                            if( loader.total === null || remainder > 0 ){
                                loader.currentIntervalId = setTimeout(
                                    function(){ loadHelper( next, remainder ); },
                                    loader.delay
                                );
                                loader.log( '\t currentIntervalId:', loader.currentIntervalId );

                            // otherwise (base-case), don't do anything
                            } else {
                                loadFinished();
                            }

                        } else { //response === null --> base-case, server sez nuthin left
                            loadFinished();
                        }
                    }
                });
            }

            //HANDLE BASE-CASE, LAST RECURSION
            function loadFinished(){
                loader.log( loader + '.loadHelper, has finished:', loader.data );
                $( loader ).trigger( LOADED_ALL_EVENT, [ loader.data, loader.total ] );
                if( callback ){ callback( loader.data ); }
            }
        },

        toString : function(){ return 'LazyDataLoader'; }
    });

    loader.initialize( config );
    return loader;
}

//==============================================================================
