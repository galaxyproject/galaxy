<%inherit file="../grid_base.mako"/>

<!-- history grid.mako -->
<%def name="load( embedded=False, insert=None )">
    ${parent.load( embedded=embedded, insert=insert )}

    <script type="text/javascript">
        // an hack for which to override the url based history copy function in the popupmenus
        // and replace it with a dialog that uses the API instead
        require([
            'mvc/history/history-model',
            'mvc/history/copy-dialog'
        ], function( mHistory, historyCopyDialog ){

            // callbacks
            function tellTheUserItFailed(){
                // history failed to copy, put the relevant techy crap in the console and alert the user
                console.error( arguments );
                alert( "${_('History could not be fetched. Please contact an administrator')}" );
            }
            function refreshEverything(){
                // history was copied
                // if we're in a frame, check for the parent Galaxy and try to refresh the history
                if( window.parent && window.parent.Galaxy && window.parent.Galaxy.currHistoryPanel ){
                    window.parent.Galaxy.currHistoryPanel.loadCurrentHistory();
                }
                // in any case reload the save history panel
                window.location.reload( true );
            }

            // for each popupmenu, (this == a popup activator button), remove the link and add a click function
            // that fetches the history and shows a copy dialog for it
            function ovipositCopyDialog( i ){
                var $this = $( this ),
                    $link = $this.children( '.menubutton-label' ),
                    // TODO: ohdearlord. stahp.
                    historyId = ( $link.attr( 'href' ).match( /id=(\w+)/ ) || [] )[1],
                    menuOptions = $this.data( 'popupmenu' ).options,
                    copyOption  = menuOptions.filter( function( o ){ return o.html === 'Copy' })[0];

                copyOption.href = 'javascript:void(0)';
                copyOption.func = function copyOptionClicked( ev ){
                    ev.preventDefault();
                    var history = new mHistory.History({ id : historyId });
                    history.fetch()
                        .fail( tellTheUserItFailed )
                        .done( function(){
                            historyCopyDialog( history ).done( refreshEverything );
                        });
                }
            }

            // wait for page ready and set it all up
            $(function(){
                var $buttons = $( '.popup.menubutton' ).each( ovipositCopyDialog );
            });
        });
    </script>
</%def>
