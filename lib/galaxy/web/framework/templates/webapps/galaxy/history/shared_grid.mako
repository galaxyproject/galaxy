<%inherit file="../grid_base.mako"/>

<%namespace file="grid_js.mako" import="copy_dialog_hack" />
<%def name="load( embedded=False, insert=None )">
    <!-- shared history grid.mako -->
    ${parent.load( embedded=embedded, insert=insert )}

    ## define the module required below
    ${copy_dialog_hack()}
    <script type="text/javascript">
        require([
            'copy-dialog-hack',
            'mvc/history/history-model',
            'utils/ajax-queue'
        ], function( copyDialogHack, HISTORY, AJAX_QUEUE ){

            function sharedNameFn( name, owner ){
                return [ _l( 'Copy of' ), name, _l( 'shared by' ), owner, _l( '(active items only)' ) ].join( ' ' );
            }

            // ---------------------------------------------------------------- insert a popupmenu multiple copy
            function findHistoryId( menuButton ){
                return $( menuButton ).children( 'label' ).attr( 'id' );
            }

            // wait for page ready and set it all up
            $(function(){
                var $buttons = $( '.popup.menubutton' ).each( function( i ){
                    // ugh. up to the row, then the text of the last cell
                    var sharedBy = $( this ).parent().parent().children('td:last-child').text(),
                        dialogOptions = {
                            allowAll : false,
                            nameFn : function( o ){
                                return sharedNameFn( "'" + _.escape( o.name ) + "'", sharedBy );
                            }
                        };

                    copyDialogHack.call( this, i, findHistoryId, dialogOptions );
                });
            });

            // ---------------------------------------------------------------- insert a new 'for n histories' copy
            var setAsCurrent = false,
                allDatasets = false;
            // a function that accepts a number of history ids, attempts to copy them via the API, and update the user
            function ajaxCopyMultipleHistories( historyData ){
                if( !historyData.length ){ return jQuery.when(); }

                var queue = new AJAX_QUEUE.AjaxQueue( historyData.map( function( data ){
                    // create a series of functions that make ajax calls from the data scraped from the grid table
                    return function(){
                        var history = new HISTORY.History({ id: data.id });
                        return history.copy( setAsCurrent, sharedNameFn( data.name, data.owner ), allDatasets );
                    }
                }));
                // quick and dirty qarl
                queue.progress( function( call ){
                    // show a timed message (like what existing before) that each has been copied
                    var $msg = $( '<div class="donemessage"/>' )
                            .text( '"' + call.response.name + '" copied' )
                            .css( 'margin-bottom', '4px' );
                    $( '#grid-message' ).append( $msg );
                    _.delay( function(){ $msg.remove() }, 5000 );
                });
                return queue;
            }

            // wait for page ready and set it all up
            $(function(){
                // remove any previous handlers and actual hrefs
                var $copyMultipleBtn = $( '.operation-button[value="Copy"]' )
                    .off( 'click' ).attr( 'href', 'javascript:void(0)' );

                // insert a function that gathers all ids, names, and users and sends them to the ajax queue
                $copyMultipleBtn.click( function( ev ){
                    ev.preventDefault();
                    var ids = $( '#grid-table td:first-child input:checked' ).toArray().map( function( input ){
                        var $tr = $( input ).parent().parent();
                        return {
                            id      : input.getAttribute( 'id' ),
                            owner   : $tr.children( 'td:last-child' ).text(),
                            name    : $tr.find( 'td:nth-child(2) .popup.menubutton label' ).text(),
                        };
                    });
                    ajaxCopyMultipleHistories( ids )
                        .fail( function(){
                            console.error( 'multiple copy failed:', arguments );
                            $( '#grid-message' ).html([
                                '<div class="donemessage">',
                                    _l( 'An error occurred during a copy. Please contact a Galaxy administrator.' ),
                                '</div>'
                            ].join( '' ));
                        });
                });
            });

        });
    </script>
</%def>
