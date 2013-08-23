/** Hack div to clear re-enclose float'd elements above it in the parent div
 */
Handlebars.registerPartial( 'clearFloatDiv', function( options ){
    return '<div class="clear"></div>';
});
/** Renders a warning in a (mostly css) highlighted, iconned warning box
 */
Handlebars.registerHelper( 'warningmessagesmall', function( options ){
    return '<div class="warningmessagesmall"><strong>' + options.fn( this ) + '</strong></div>'
});
/** Calls _l (from base-mvc.js) to localize strings (if poosible)
 *  This helper is specifically for localization within templates
 */
Handlebars.registerHelper( 'local', function( options ){
    return _l( options.fn( this ) );
});