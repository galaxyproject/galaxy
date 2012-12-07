/**
 * -- Functions for creating large UI elements. --
 */
// =============================================================================
/**
 * -- Utility models and views for Galaxy objects. --
 */
 
/**
 * Clickable button represented as an icon.
 */
var IconButton = Backbone.Model.extend({
    defaults: {
        title: "",
        icon_class: "",
        on_click: null,
        menu_options: null,
        tooltip_config: {},
        
        isMenuButton : true,
        id          : null,
        href        : null,
        target      : null,
        enabled     : true,
        visible     : true
    }
    
    //validate : function( attributes ){
        //TODO: validate href or on_click
        //TODO: validate icon_class
    //}
});


/**
 *  
 */
var IconButtonView = Backbone.View.extend({
    
    initialize  : function(){
        // better rendering this way (for me anyway)
        this.model.attributes.tooltip_config = { placement : 'bottom' };
        this.model.bind( 'change', this.render, this );
    },
    
    render : function(){
        //NOTE: not doing this hide will lead to disappearing buttons when they're both being hovered over & rendered
        this.$el.tooltip( 'hide' );
        
        // template in common-templates.html 
        var newElem = $( Handlebars.partials.iconButton( this.model.toJSON() ) );
        newElem.tooltip( this.model.get( 'tooltip_config' ) );
        
        this.$el.replaceWith( newElem );
        this.setElement( newElem );

        return this;
    },
    
    events      : {
        'click' : 'click'
    },
    
    click : function( event ){
        // if on_click pass to that function
        if( this.model.attributes.on_click ){
            this.model.attributes.on_click( event );
            return false;
        }
        // otherwise, bubble up (to href or whatever)
        return true;
    }
});
//TODO: bc h.templates is gen. loaded AFTER ui, Handlebars.partials.iconButton === undefined
IconButtonView.templates = {
    iconButton : Handlebars.partials.iconButton
};

var IconButtonCollection = Backbone.Collection.extend({
    model: IconButton
});


//------------------------------------------------------------------------------
/**
 * Menu with multiple icon buttons. Views are not needed nor used for individual buttons.
 */
var IconButtonMenuView = Backbone.View.extend({
    tagName: 'div',

    initialize: function() {
        this.render();
    },
    
    render: function() {
        var self = this;
        this.collection.each(function(button) {
            // Create and add icon button to menu.
            var elt = 
            $('<a/>').attr('href', 'javascript:void(0)')
                     .attr('title', button.attributes.title)
                     .addClass('icon-button menu-button')
                     .addClass(button.attributes.icon_class)
                     .appendTo(self.$el)
                     .click(button.attributes.on_click);

            if (button.attributes.tooltip_config) {
                elt.tooltip(button.attributes.tooltip_config);
            }

            // If there are options, add popup menu to icon.
            var menu_options = button.get('options');
            if (menu_options) {
                make_popupmenu(elt, menu_options);
            }
        
        });
        return this;
    }
});

/**
 * Returns an IconButtonMenuView for the provided configuration.
 * Configuration is a list of dictionaries where each dictionary
 * defines an icon button. Each dictionary must have the following
 * elements: icon_class, title, and on_click.
 */
var create_icon_buttons_menu = function(config, global_config) {
    if (!global_config) { global_config = {}; }

    // Create and initialize menu.
    var buttons = new IconButtonCollection( 
            _.map(config, function(button_config) { 
                return new IconButton(_.extend(button_config, global_config)); 
            })
        );
    
    return new IconButtonMenuView( {collection: buttons} );
};


// =============================================================================
/**
 * 
 */
var Grid = Backbone.Collection.extend({
    
});

/**
 *
 */
var GridView = Backbone.View.extend({
    
});

// =============================================================================
/**
 * Necessary Galaxy paths.
 */
var GalaxyPaths = Backbone.Model.extend({
    defaults: {
        root_path: "",
        image_path: ""
    }
});


// =============================================================================
/** @class View for a popup menu
 *  @name PopupMenu
 *
 *  @constructs
 */
var PopupMenu = Backbone.View.extend(
/** @lends PopupMenu.prototype */{

    /* TODO:
        add submenus
        add hrefs
        test various html keys
        add make_popupmenus style
        get template inside this file somehow
    */
    /** Cache the desired button element and options, set up the button click handler
     *  NOTE: attaches this view as HTML/jQ data on the button for later use.
     */
    //TODO: include docs on special option keys (divider, checked, etc.)
    initialize : function( $button, options ){
        // default settings
        this.$button = $button || $( '<div/>' );
        this.options = options || [];
        //console.debug( this + '.initialize, button:', $button, ', options:', options );

        // set up button click -> open menu behavior
        var menu = this;
        this.$button.click( function( event ){
            menu._renderAndShow( event );
            //event.stopPropagation();
            return false;
        });

        // attach this view as a data object on the button - for later access
        //TODO:?? memleak?
        this.$button.data( 'PopupMenu', this );

        // template loading is problematic - ui is loaded in base.mako
        //  and the template (prev.) needed to be loaded before ui
        if( !this.templates.wrapper ){
            this.templates.wrapper = Handlebars.templates[ 'template-popupmenu-wrapper' ];
        }
    },

    /** Render the menu. NOTE: doesn't attach itself to the DOM.
     *  @see PopupMenu#_renderAndShow
     */
    render : function(){
        var menu = this;

        // render the menu body
        this.$el.addClass( 'popmenu-wrapper' )
            .css({
                position:   'absolute',
                display:    'none'
            });

        //BUG: anchors within a.popupmenu-option render OUTSIDE the a.popupmenu-option!?
        this.$el.html( PopupMenu.templates.menu({
            options     : this.options,
            // sets menu div id to '{{ id }}-menu'
            id          : this.$button.attr( 'id' )
        }));
        //console.debug( this.$el, ':', this.$el.html() );

        // set up behavior on each link/anchor elem
        if( this.options.length ){
            this.$el.find( 'li' ).each( function( i, li ){
                var $li = $( li ),
                    $anchor = $li.children( 'a.popupmenu-option' ),
                    menuFunc = menu.options[ i ].func;

                //console.debug( 'setting up behavior:', i, menu.options[ i ], $li, $anchor );
                if( $anchor.length && menuFunc ){
                    $anchor.click( function( event ){
                        menuFunc( event, menu.options[ i ] );
                    });
                }

                // cache the anchor as a jq obj within the options obj
                menu.options[ i ].$li = $li;
            });
        }
        return this;
    },

    /** Get the absolute position/offset for the menu
     */
    _getShownPosition : function( clickEvent ){
        var menuWidth = this.$el.width(),
            // display menu horiz. centered on click...
            x = clickEvent.pageX - menuWidth / 2 ;

        // ...but adjust that to handle horiz. scroll and window dimensions (draw entirely on visible screen area)
        x = Math.min( x, $( document ).scrollLeft() + $( window ).width() - menuWidth - 5 );
        x = Math.max( x, $( document ).scrollLeft() + 5 );

        return {
            top: clickEvent.pageY,
            left: x
        };
    },

    /** Render the menu, append to the page body at the click position, and set up the 'click-away' handlers, show
     */
    _renderAndShow : function( clickEvent ){
        this.render();
        this.$el.appendTo( 'body' );
        this.$el.css( this._getShownPosition( clickEvent ) );
        this._setUpCloseBehavior();
        this.$el.show();
    },

    /** Bind an event handler to all available frames so that when anything is clicked
     *      * the menu is removed from the DOM
     *      * The event handler unbinds itself
     */
    _setUpCloseBehavior : function(){
        var menu = this,
            // function to close popup and unbind itself
            closePopupWhenClicked = function( $elClicked ){
                $elClicked.bind( "click.close_popup", function(){
                    menu.remove();
                    $elClicked.unbind( "click.close_popup" );
                });
            };

        // bind to current, parent, and sibling frames
        //TODO: (Assuming for now that this is the best way to do this...)
        closePopupWhenClicked( $( window.document ) );
        closePopupWhenClicked( $( window.top.document ) );
        _.each( window.top.frames, function( siblingFrame ){
            closePopupWhenClicked( $( siblingFrame.document ) );
        });
    },

    /** Add a menu option/item at the given index
     */
    addItem : function( item, index ){
        // append to end if no index
        index = ( index >= 0 )?( index ):( this.options.length );
        this.options.splice( index, 0, item );
        return this;
    },

    /** Remove a menu option/item at the given index
     */
    removeItem : function( index ){
        if( index >=0 ){
            this.options.splice( index, 1 );
        }
        return this;
    },

    /** Search for a menu option by it's html
     */
    findIndexByHtml : function( html ){
        for( var i=0; i<this.options.length; i++ ){
            if( ( _.has( this.options[i], 'html' ) )
            &&  ( this.options[i].html === html ) ){
                return i;
            }
        }
        return null;
    },

    /** Search for a menu option by it's html
     */
    findItemByHtml : function( html ){
        return this.options[( this.findIndexByHtml( html ) )];
    },

    /** String representation. */
    toString : function(){
        return 'PopupMenu';
    }
});
PopupMenu.templates = {
    menu    : Handlebars.templates[ 'template-popupmenu-menu' ]
};

// -----------------------------------------------------------------------------
// the following class functions are bridges from the original make_popupmenu and make_popup_menus
//  to the newer backbone.js PopupMenu

/** Create a PopupMenu from simple map initial_options activated by clicking button_element.
 *      Converts initial_options to object array used by PopupMenu.
 *  @param {jQuery|DOMElement} button_element element which, when clicked, activates menu
 *  @param {Object} initial_options map of key -> values, where
 *      key is option text, value is fn to call when option is clicked
 *  @returns {PopupMenu} the PopupMenu created
 */
PopupMenu.make_popupmenu = function( button_element, initial_options ){
    var convertedOptions = [];
    _.each( initial_options, function( optionVal, optionKey ){
        var newOption = { html: optionKey };

        // keys with null values indicate: header
        if( optionVal === null ){ // !optionVal? (null only?)
            newOption.header = true;

        // keys with function values indicate: a menu option
        } else if( jQuery.type( optionVal ) === 'function' ){
            newOption.func = optionVal;
        }
        //TODO:?? any other special optionVals?
        // there was no divider option originally
        convertedOptions.push( newOption );
    });
    return new PopupMenu( $( button_element ), convertedOptions );
};

/** Find all anchors in $parent (using selector) and covert anchors into a PopupMenu options map.
 *  @param {jQuery} $parent the element that contains the links to convert to options
 *  @param {String} selector jq selector string to find links
 *  @returns {Object[]} the options array to initialize a PopupMenu
 */
//TODO: lose parent and selector, pass in array of links, use map to return options
PopupMenu.convertLinksToOptions = function( $parent, selector ){
    $parent = $( $parent );
    selector = selector || 'a';
    var options = [];
    $parent.find( selector ).each( function( elem, i ){
        var option = {},
            $link = $( elem );

        // convert link text to the option text (html) and the href into the option func
        option.html = $link.text();
        if( linkHref ){
            var linkHref    = $link.attr( 'href' ),
                linkTarget  = $link.attr( 'target' ),
                confirmText = $link.attr( 'confirm' );

            option.func = function(){
                // if there's a "confirm" attribute, throw up a confirmation dialog, and
                //  if the user cancels - do nothing
                if( ( confirmText ) && ( !confirm( confirmText ) ) ){ return; }

                // if there's no confirm attribute, or the user accepted the confirm dialog:
                var f;
                switch( linkTarget ){
                    // relocate the center panel
                    case '_parent':
                        window.parent.location = linkHref;
                        break;

                    // relocate the entire window
                    case '_top':
                        window.top.location = linkHref;
                        break;

                    // Http request target is a window named demolocal on the local box
                    //TODO: I still don't understand this option (where the hell does f get set? confirm?)
                    case 'demo':
                        if( f === undefined || f.closed ){
                            f = window.open( linkHref, linkTarget );
                            f.creator = self;
                        }
                        break;

                    // relocate this panel
                    default:
                        window.location = linkHref;
                }
            };
        }
        options.push( option );
    });
    return options;
};

/** Create a single popupmenu from existing DOM button and anchor elements
 *  @param {jQuery} $buttonElement the element that when clicked will open the menu
 *  @param {jQuery} $menuElement the element that contains the anchors to convert into a menu
 *  @param {String} menuElementLinkSelector jq selector string used to find anchors to be made into menu options
 *  @returns {PopupMenu} the PopupMenu (Backbone View) that can render, control the menu
 */
PopupMenu.fromExistingDom = function( $buttonElement, $menuElement, menuElementLinkSelector ){
    $buttonElement = $( $buttonElement );
    $menuElement = $( $menuElement );
    var options = PopupMenu.convertLinksToOptions( $menuElement, menuElementLinkSelector );
    // we're done with the menu (having converted it to an options map)
    $menuElement.remove();
    return new PopupMenu( $buttonElement, options );
};

/** Create all popupmenus within a document or a more specific element
 *  @param {DOMElement} parent the DOM element in which to search for popupmenus to build (defaults to document)
 *  @param {String} menuSelector jq selector string to find popupmenu menu elements (defaults to "div[popupmenu]")
 *  @param {Function} buttonSelectorBuildFn the function to build the jq button selector.
 *      Will be passed $menuElement, parent.
 *      (Defaults to return '#' + $menuElement.attr( 'popupmenu' ); )
 *  @returns {PopupMenu[]} array of popupmenus created
 */
PopupMenu.make_popup_menus = function( parent, menuSelector, buttonSelectorBuildFn ){
    parent = parent || document;
    // orig. Glx popupmenu menus have a (non-std) attribute 'popupmenu'
    //  which contains the id of the button that activates the menu
    menuSelector = menuSelector || 'div[popupmenu]';
    // default to (orig. Glx) matching button to menu by using the popupmenu attr of the menu as the id of the button
    buttonSelectorBuildFn = buttonSelectorBuildFn || function( $menuElement, parent ){
        return '#' + $menuElement.attr( 'popupmenu' );
    };

    // aggregate and return all PopupMenus
    var popupMenusCreated = [];
    $( parent ).find( menuSelector ).each( function(){
        var $menuElement    = $( this ),
            $buttonElement  = $( parent ).find( buttonSelectorBuildFn( $menuElement, parent ) );
        popupMenusCreated.push( PopupMenu.fromDom( $buttonElement, $menuElement ) );
        $buttonElement.addClass( 'popup' );
    });
    return popupMenusCreated;
}

