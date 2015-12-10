<%inherit file="../grid_base.mako"/>

<%namespace file="grid_js.mako" import="copy_dialog_hack" />
<%def name="load( embedded=False, insert=None )">
    <!-- shared history grid.mako -->
    ${parent.load( embedded=embedded, insert=insert )}

    ## define the module required below
    ${copy_dialog_hack()}
    <script type="text/javascript">
        require([ 'copy-dialog-hack' ], function( copyDialogHack ){
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
                                // special special name
                                var name = "'" + _.escape( o.name ) + "'";
                                return [
                                    _l( 'Copy of' ), name, _l( 'shared by' ), sharedBy, _l( '(active items only)' )
                                ].join( ' ' );
                            }
                        };

                    copyDialogHack.call( this, i, findHistoryId, dialogOptions );
                });

                ## TODO: multiple copy
            });
        });
    </script>
</%def>
