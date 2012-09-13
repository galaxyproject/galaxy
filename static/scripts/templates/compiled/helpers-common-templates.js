/** Hack div to clear re-enclose float'd elements above it in the parent div
 */
Handlebars.registerPartial( 'clearFloatDiv', function( options ){
    return '<div class="clear"></div>';
});
/** Renders a glx style icon-button (see IconButton in mvc/ui.js)
 *      can be used in either of the following ways:
 *          within a template: {{> iconButton buttonData}}
 *          from js: var templated = ( Handlebars.partials.iconButton( buttonData ) );
 */         
Handlebars.registerPartial( 'iconButton', function( buttonData, options ){
    var buffer = "";
    buffer += ( buttonData.enabled )?( '<a' ):( '<span' );
    
    if( buttonData.title ){ buttonData.buffer += ' title="' + buttonData.title + '"'; }
    
    buffer += ' class="icon-button';
    if( buttonData.isMenuButton ){ buffer += ' menu-button'; }
    if( buttonData.title        ){ buffer += ' tooltip'; }
    buffer += ' ' + buttonData.icon_class;
    if( !buttonData.enabled     ){ buffer += '_disabled'; }
    buffer += '"';
    
    if( buttonData.id ){ buffer += ' id="' + buttonData.id + '"'; }
    buffer += ' href="' + ( ( buttonData.href )?( buttonData.href ):( 'javascript:void(0);' ) ) + '"';
    if( buttonData.target ){ buffer += ' target="' + buttonData.target + '"'; }
    
    if( !buttonData.visible ){ buffer += ' style="display: none;"'; }
    
    buffer += '>Bler' + ( ( buttonData.enabled )?( '</a>' ):( '</span>' ) );
    return buffer;
});
/** Renders a warning in a (mostly css) highlighted, iconned warning box
 */
Handlebars.registerHelper( 'warningmessagesmall', function( options ){
    return '<div class="warningmessagesmall"><strong>' + options.fn( this ) + '</strong></div>'
});
