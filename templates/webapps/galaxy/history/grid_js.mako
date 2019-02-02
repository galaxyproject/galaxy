<%def name="copy_dialog_hack()">
    ## TODO: remove!!!!! when grids are iterated over again
    <script type="text/javascript">
        // define a module that has:
        // an hack for which to override the url based history copy function in the popupmenus
        // and replace it with a dialog that uses the API instead
        define( 'copy-dialog-hack', [
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

            // get the id from the dom somehow (the two doms (saved/shared) are different...)
            function findHistoryId( $menuButton ){
                var title = '${grid.title}';
                if( title === 'Saved Histories' ){
                    var $link = $menuButton.children( '.menubutton-label' );
                    // TODO: ohdearlord. stahp.
                    return ( $link.attr( 'href' ).match( /id=(\w+)/ ) || [] )[1];
                }
                // Histories shared with you
                var $label = $menuButton.children( 'label' );
                return $label.attr( 'id' );
            }

            // for each popupmenu, (this == a popup activator button), remove the link and add a click function
            // that fetches the history and shows a copy dialog for it
            // pass in a fn for extracting the id from the dom and an (optional) object with dialog options
            function copyDialogHack( i, historyIdFindFn, dialogOptions ){
                dialogOptions = dialogOptions || {};
                var $this = $( this ),
                    historyId = historyIdFindFn( this ),
                    menuOptions = $this.data( 'popupmenu' ).options,
                    copyOption  = menuOptions.filter( function( o ){ return o.html === 'Copy' })[0];

                copyOption.href = 'javascript:void(0)';
                copyOption.func = function copyOptionClicked( ev ){
                    ev.preventDefault();
                    var history = new mHistory.History({ id : historyId });
                    history.fetch()
                        .fail( tellTheUserItFailed )
                        .done( function(){
                            historyCopyDialog( history, dialogOptions ).done( refreshEverything );
                        });
                }
            }
            return copyDialogHack;
        });
    </script>
</%def>
