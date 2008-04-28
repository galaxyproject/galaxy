jQuery(document).ready( function() {
    // Links with confirmation
    jQuery( "a[@confirm]" ).click( function() {
        return confirm( jQuery(this).attr( "confirm"  ) )
    })
    
});