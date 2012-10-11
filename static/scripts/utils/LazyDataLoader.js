/*
TODO:
    ?? superclass dataloader, subclass lazydataloader??

*/
//==============================================================================
/**
 *  Object to progressively load JSON data from a REST url, delaying some time between loading chunks
 *
 *  Data from ajax loading is aggregated in a list, with one element for each ajax response.
 *  It's up to the calling code to combine the results in a meaningful, correct way
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
 *      
 *      loadedPartialEvent    : 'loader.partial',
 *      loadedAllEvent        : 'loader.all',
 *  });
 *  $( loader ).bind( 'loader.partial', function( event, data ){
 *      console.info( 'partial load complete:', event, data );
 *      // ... do stuff with new data
 *  });
 *  $( loader ).bind( 'loader.all', function( event, data ){
 *      console.info( 'final load complete:', event, data );
 *      // ... do stuff with all data
 *  });
 *  
 *  loader.load( function( dataArray ){ console.debug( 'FINISHED!', x, y, z ); } );
 */
function LazyDataLoader( config ){
    // for now assume:
    //  get, async, and params sent via url query string
    //  we want json
    //  we know the size of the data on the server beforehand
    var loader = this;
    
    jQuery.extend( loader, LoggableMixin );
    jQuery.extend( loader, {
    
        //NOTE: the next two need to be sent in config (required)
        // total size of data on server
        total   : undefined,
        // url of service to get the data
        url     : undefined,
        
        // holds the interval id for the current load delay
        currentIntervalId   : undefined,
        
        // optional events to trigger when partial, last data are loaded
        //  loadedPartialEvent will be sent: the ajax response data, start value, and size
        loadedPartialEvent  : undefined,
        //  loadedAllEvent will be sent: the final loader's data array and the total
        loadedAllEvent      : undefined,
        
        // each load call will add an element to this array
        //  it's the responsibility of the code using this to combine them properly
        data    : [],
        // ms btwn recursive loads
        delay   : 500,
        // starting line, element, whatever
        start   : 0,
        // size to fetch per load
        size    : 1000,
        
        // loader init func: extends loader with config and calls config.init if there
        //@param {object} config : object containing variables to override (or additional)
        initialize : function( config ){
            jQuery.extend( loader, config );
            
            // call the custom initialize function if any
            //  only dangerous if the user tries LazyDataLoader.prototype.init
            if( config.hasOwnProperty( 'initialize' ) ){
                config.initialize.call( loader, config );
            }
            
            // ensure necessary stuff
            if( !loader.total ){ throw( loader + ' requires a total (total size of the data)' ); }
            if( !loader.url ){ throw( loader + ' requires a url' ); }
            
            this.log( this + ' initialized:', loader );
        },
        
        // returns query string formatted start and size (for the next fetch) appended to the loader.url
        //OVERRIDE: to change how params are passed, param names, etc.
        //@param {int} start : the line/row/datum indicating where in the dataset the next load begins
        //@param {int} size : the number of lines/rows/data to get on the next load
        buildUrl : function( start, size ){
            // currently VERY SPECIFIC to using data_providers.py start_val, max_vals params
            return loader.url + '&' + jQuery.param({
                start_val: start,
                max_vals:  size
            });
        },
        
        //OVERRIDE: to handle ajax errors differently
        ajaxErrorFn : function( xhr, status, error ){
            alert( loader + ' ERROR:' + status + '\n' + error );
        },

        // interface to begin load (and first recursive call)
        //@param {Function} callback : function to execute when all data is loaded. callback is passed loader.data 
        load : function( callback ){
            
            // subsequent recursive calls
            function loadHelper( start, size ){
                loader.log( loader + '.loadHelper, start:', start, 'size:', size );
                var url = loader.buildUrl( start, size );
                loader.log( '\t url:', url );
                
                jQuery.ajax({
                    url         : loader.buildUrl( start, size ),
                    dataType    : 'json',
                    error       : function( xhr, status, error ){
                        loader.log( '\t ajax error, status:', status, 'error:', error );
                        if( loader.currentIntervalId ){
                            clearInterval( loader.currentIntervalId );
                        }
                        loader.ajaxErrorFn( xhr, status, error );
                    },
                    
                    success     : function( response ){
                        var next = start + size,
                            remainder = Math.min( loader.total - next, loader.size );
                        loader.log( '\t ajax success, next:', next, 'remainder:', remainder );
                            
                        // store the response as is in a new element
                        //TODO:?? store start, size as well?
                        loader.data.push( response );
                        
                        // fire the partial load event
                        if( loader.loadedPartialEvent ){
                            loader.log( '\t firing:', loader.loadedPartialEvent );
                            $( loader ).trigger( loader.loadedPartialEvent, response, start, size );
                        }
                        
                        // if we haven't gotten everything yet,
                        //  set up for next recursive call and set the timer
                        if( remainder > 0 ){
                            loader.currentIntervalId = setTimeout(
                                function(){ loadHelper( next, remainder ); },
                                loader.delay
                            );
                            loader.log( '\t currentIntervalId:', loader.currentIntervalId );
                            
                        // otherwise (base-case), don't do anything
                        } else {
                            loader.log( loader + '.loadHelper, has finished:', loader.data );
                            if( loader.loadedAllEvent ){
                                loader.log( '\t firing:', loader.loadedAllEvent );
                                $( loader ).trigger( loader.loadedAllEvent, loader.data, loader.total );
                            }
                            if( callback ){ callback( loader.data ); }
                        }
                    }
                });
            }
            loadHelper( loader.start, Math.min( loader.total, loader.size ) );
        },
    
        toString : function(){ return 'LazyDataLoader'; }
    });
    
    loader.initialize( config );
    return loader;
}

