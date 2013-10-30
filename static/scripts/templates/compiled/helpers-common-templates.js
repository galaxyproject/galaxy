/** Calls _l (from base-mvc.js) to localize strings (if poosible)
 *  This helper is specifically for localization within templates
 */
Handlebars.registerHelper( 'local', function( options ){
    return _l( options.fn( this ) );
});
/** replace newlines with breaks */
Handlebars.registerHelper( 'n2br', function( options ){
    return options.fn( this ).replace( /\n/g, '<br/>' );
});