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

            // wait for page ready and set it all up, do it again when the grid refreshes
            $(function(){
                if( !gridView ){
                    console.warn( 'no grid' );
                    return;
                }

                function replaceCopyFunction(){
                    gridView.$( '.popup.menubutton' ).each( function( i ){
                        copyDialogHack.call( this, i, findHistoryId );
                    });
                }
                replaceCopyFunction();

                var originalInitGrid = gridView.init_grid;
                gridView.init_grid = function __patched_init_grid( json ){
                    originalInitGrid.call( gridView, json );
                    replaceCopyFunction();
                };
            });
        });
    </script>
</%def>
