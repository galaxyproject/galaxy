<%inherit file="../grid_base.mako"/>

<%namespace file="grid_js.mako" import="copy_dialog_hack" />
<%def name="load( embedded=False, insert=None )">
    <!-- saved history grid.mako -->
    ${parent.load( embedded=embedded, insert=insert )}

    ## define the module required below
    ${copy_dialog_hack()}
    <script type="text/javascript">
        require([ 'copy-dialog-hack' ], function( copyDialogHack ){
            function findHistoryId( menuButton ){
                var $link = $( menuButton ).children( '.menubutton-label' );
                // TODO: ohdearlord. stahp.
                return ( $link.attr( 'href' ).match( /id=(\w+)/ ) || [] )[1];
            }

            // wait for page ready and set it all up
            $(function(){
                var $buttons = $( '.popup.menubutton' ).each( function( i ){
                    copyDialogHack.call( this, i, findHistoryId );
                });
            });
        });
    </script>
</%def>
