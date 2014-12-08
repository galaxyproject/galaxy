/**
 * functions for creating major ui elements
 */

/**
 * backbone model for icon buttons
 */
var IconButton = Backbone.Model.extend({
    defaults: {
        title           : "",
        icon_class      : "",
        on_click        : null,
        menu_options    : null,
        is_menu_button  : true,
        id              : null,
        href            : null,
        target          : null,
        enabled         : true,
        visible         : true,
        tooltip_config  : {}
    }
});

/**
 *  backbone view for icon buttons
 */
var IconButtonView = Backbone.View.extend({

    initialize : function(){
        // better rendering this way
        this.model.attributes.tooltip_config = { placement : 'bottom' };
        this.model.bind( 'change', this.render, this );
    },

    render : function( ){
        // hide tooltip
        this.$el.tooltip( 'hide' );
        
        var new_elem = this.template( this.model.toJSON() );
        // configure tooltip
        new_elem.tooltip( this.model.get( 'tooltip_config' ));
        this.$el.replaceWith( new_elem );
        this.setElement( new_elem );
        return this;
    },
    
    events : {
        'click' : 'click'
    },
    
    click : function( event ){
        // if on_click pass to that function
        if( _.isFunction( this.model.get( 'on_click' ) ) ){
            this.model.get( 'on_click' )( event );
            return false;
        }
        // otherwise, bubble up ( to href or whatever )
        return true;
    },
    
    // generate html element
    template: function( options ){
        var buffer = 'title="' + options.title + '" class="icon-button';
    
        if( options.is_menu_button ){
            buffer += ' menu-button';
        }
        
        buffer += ' ' + options.icon_class;
    
        if( !options.enabled ){
            buffer += '_disabled';
        }
        
        // close class tag
        buffer += '"';
    
        if( options.id ){
            buffer += ' id="' + options.id + '"';
        }
        
        buffer += ' href="' + options.href + '"';
        // add target for href
        if( options.target ){
            buffer += ' target="' + options.target + '"';
        }
        // set visibility
        if( !options.visible ){
            buffer += ' style="display: none;"';
        }
    
        // enabled/disabled
        if ( options.enabled ){
            buffer = '<a ' + buffer + '/>';
        } else {
            buffer = '<span ' + buffer + '/>';
        }
            
        // return element
        return $( buffer );
    }
} );

// define collection
var IconButtonCollection = Backbone.Collection.extend({
    model: IconButton
});

/**
 * menu with multiple icon buttons
 * views are not needed nor used for individual buttons
 */
var IconButtonMenuView = Backbone.View.extend({

    tagName: 'div',

    initialize: function(){
        this.render();
    },
    
    render: function(){
        // initialize icon buttons
        var self = this;
        this.collection.each(function(button){
            // create and add icon button to menu
            var elt = $('<a/>')
                .attr('href', 'javascript:void(0)')
                .attr('title', button.attributes.title)
                .addClass('icon-button menu-button')
                .addClass(button.attributes.icon_class)
                .appendTo(self.$el)
                .click(button.attributes.on_click);

            // configure tooltip
            if (button.attributes.tooltip_config){
                elt.tooltip(button.attributes.tooltip_config);
            }

            // add popup menu to icon
            var menu_options = button.get('options');
            if (menu_options){
                make_popupmenu(elt, menu_options);
            }
        });
        
        // return
        return this;
    }
});

/**
 * Returns an IconButtonMenuView for the provided configuration.
 * Configuration is a list of dictionaries where each dictionary
 * defines an icon button. Each dictionary must have the following
 * elements: icon_class, title, and on_click.
 */
var create_icon_buttons_menu = function(config, global_config)
{
    // initialize global configuration
    if (!global_config) global_config = {};

    // create and initialize menu
    var buttons = new IconButtonCollection( 
        _.map(config, function(button_config){
            return new IconButton(_.extend(button_config, global_config));
        })
    );
    
    // return menu
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
 * view for a popup menu
 */
var PopupMenu = Backbone.View.extend({
//TODO: maybe better as singleton off the Galaxy obj
    /** Cache the desired button element and options, set up the button click handler
     *  NOTE: attaches this view as HTML/jQ data on the button for later use.
     */
    initialize: function( $button, options ){
        // default settings
        this.$button = $button;
        if( !this.$button.size() ){
            this.$button = $( '<div/>' );
        }
        this.options = options || [];

        // set up button click -> open menu behavior
        var menu = this;
        this.$button.click( function( event ){
            // if there's already a menu open, remove it
            $( '.popmenu-wrapper' ).remove();
            menu._renderAndShow( event );
            return false;
        });
    },

    // render the menu, append to the page body at the click position, and set up the 'click-away' handlers, show
    _renderAndShow: function( clickEvent ){
        this.render();
        this.$el.appendTo( 'body' ).css( this._getShownPosition( clickEvent )).show();
        this._setUpCloseBehavior();
    },

    // render the menu
    // this menu doesn't attach itself to the DOM ( see _renderAndShow )
    render: function(){
        // render the menu body absolute and hidden, fill with template
        this.$el.addClass( 'popmenu-wrapper' ).hide()
            .css({ position : 'absolute' })
            .html( this.template( this.$button.attr( 'id' ), this.options ));

        // set up behavior on each link/anchor elem
        if( this.options.length ){
            var menu = this;
            //precondition: there should be one option per li
            this.$el.find( 'li' ).each( function( i, li ){
                var option = menu.options[i];

                // if the option has 'func', call that function when the anchor is clicked
                if( option.func ){
                    $( this ).children( 'a.popupmenu-option' ).click( function( event ){
                        option.func.call( menu, event, option );
                        // bubble up so that an option click will call the close behavior
                        //return false;
                    });
                }
            });
        }
        return this;
    },

    template : function( id, options ){
        return [
            '<ul id="', id, '-menu" class="dropdown-menu">', this._templateOptions( options ), '</ul>'
        ].join( '' );
    },

    _templateOptions : function( options ){
        if( !options.length ){
            return '<li>(no options)</li>';
        }
        return _.map( options, function( option ){
            if( option.divider ){
                return '<li class="divider"></li>';
            } else if( option.header ){
                return [ '<li class="head"><a href="javascript:void(0);">', option.html, '</a></li>' ].join( '' );
            }
            var href   = option.href || 'javascript:void(0);',
                target = ( option.target  )?( ' target="' + option.target + '"' ):( '' ),
                check  = ( option.checked )?( '<span class="fa fa-check"></span>' ):( '' );
            return [
                '<li><a class="popupmenu-option" href="', href, '"', target, '>',
                    check, option.html,
                '</a></li>'
            ].join( '' );
        }).join( '' );
    },

    // get the absolute position/offset for the menu
    _getShownPosition : function( clickEvent ){

        // display menu horiz. centered on click...
        var menuWidth = this.$el.width();
        var x = clickEvent.pageX - menuWidth / 2 ;

        // adjust to handle horiz. scroll and window dimensions ( draw entirely on visible screen area )
        x = Math.min( x, $( document ).scrollLeft() + $( window ).width() - menuWidth - 5 );
        x = Math.max( x, $( document ).scrollLeft() + 5 );
        return {
            top: clickEvent.pageY,
            left: x
        };
    },

    // bind an event handler to all available frames so that when anything is clicked
    // the menu is removed from the DOM and the event handler unbinds itself
    _setUpCloseBehavior: function(){
        var menu = this;
//TODO: alternately: focus hack, blocking overlay, jquery.blockui

        // function to close popup and unbind itself
        function closePopup( event ){
            $( document ).off( 'click.close_popup' );
            if( window.parent !== window ){
                try {
                    $( window.parent.document ).off( "click.close_popup" );
                } catch( err ){}
            } else {
                try {
                    $( 'iframe#galaxy_main' ).contents().off( "click.close_popup" );
                } catch( err ){}
            }
            menu.remove();
        }

        $( 'html' ).one( "click.close_popup", closePopup );
        if( window.parent !== window ){
            try {
                $( window.parent.document ).find( 'html' ).one( "click.close_popup", closePopup );
            } catch( err ){}
        } else {
            try {
                $( 'iframe#galaxy_main' ).contents().one( "click.close_popup", closePopup );
            } catch( err ){}
        }
    },

    // add a menu option/item at the given index
    addItem: function( item, index ){
        // append to end if no index
        index = ( index >= 0 ) ? index : this.options.length;
        this.options.splice( index, 0, item );
        return this;
    },

    // remove a menu option/item at the given index
    removeItem: function( index ){
        if( index >=0 ){
            this.options.splice( index, 1 );
        }
        return this;
    },

    // search for a menu option by its html
    findIndexByHtml: function( html ){
        for( var i = 0; i < this.options.length; i++ ){
            if( _.has( this.options[i], 'html' ) && ( this.options[i].html === html )){
                return i;
            }
        }
        return null;
    },

    // search for a menu option by its html
    findItemByHtml: function( html ){
        return this.options[( this.findIndexByHtml( html ))];
    },

    // string representation
    toString: function(){
        return 'PopupMenu';
    }
});
/** shortcut to new for when you don't need to preserve the ref */
PopupMenu.create = function _create( $button, options ){
    return new PopupMenu( $button, options );
};

// -----------------------------------------------------------------------------
// the following class functions are bridges from the original make_popupmenu and make_popup_menus
// to the newer backbone.js PopupMenu

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
        var option = {}, $link = $( elem );

        // convert link text to the option text (html) and the href into the option func
        option.html = $link.text();
        if( $link.attr( 'href' ) ){
            var linkHref    = $link.attr( 'href' ),
                linkTarget  = $link.attr( 'target' ),
                confirmText = $link.attr( 'confirm' );

            option.func = function(){
                // if there's a "confirm" attribute, throw up a confirmation dialog, and
                //  if the user cancels - do nothing
                if( ( confirmText ) && ( !confirm( confirmText ) ) ){ return; }

                // if there's no confirm attribute, or the user accepted the confirm dialog:
                switch( linkTarget ){
                    // relocate the center panel
                    case '_parent':
                        window.parent.location = linkHref;
                        break;

                    // relocate the entire window
                    case '_top':
                        window.top.location = linkHref;
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
};


//==============================================================================
var faIconButton = function( options ){
//TODO: move out of global
    options = options || {};
    options.tooltipConfig = options.tooltipConfig || { placement: 'bottom' };

    options.classes = [ 'icon-btn' ].concat( options.classes || [] );
    if( options.disabled ){
        options.classes.push( 'disabled' );
    }

    var html = [
        '<a class="', options.classes.join( ' ' ), '"',
                (( options.title )?( ' title="' + options.title + '"' ):( '' )),
                (( !options.disabled && options.target )?  ( ' target="' + options.target + '"' ):( '' )),
                ' href="', (( !options.disabled && options.href )?( options.href ):( 'javascript:void(0);' )), '">',
            // could go with something less specific here - like 'html'
            '<span class="fa ', options.faIcon, '"></span>',
        '</a>'
    ].join( '' );
    var $button = $( html ).tooltip( options.tooltipConfig );
    if( _.isFunction( options.onclick ) ){
        $button.click( options.onclick );
    }
    return $button;
};


//==============================================================================
function LoadingIndicator( $where, options ){
//TODO: move out of global
//TODO: too specific to history panel

    var self = this;
    // defaults
    options = jQuery.extend({
        cover       : false
    }, options || {} );

    function render(){
        var html = [
            '<div class="loading-indicator">',
                '<div class="loading-indicator-text">',
                    '<span class="fa fa-spinner fa-spin fa-lg"></span>',
                    '<span class="loading-indicator-message">loading...</span>',
                '</div>',
            '</div>'
        ].join( '\n' );

        var $indicator = $( html ).hide().css( options.css || {
                position    : 'fixed'
            }),
            $text = $indicator.children( '.loading-indicator-text' );

        if( options.cover ){
            $indicator.css({
                'z-index'   : 2,
                top         : $where.css( 'top' ),
                bottom      : $where.css( 'bottom' ),
                left        : $where.css( 'left' ),
                right       : $where.css( 'right' ),
                opacity     : 0.5,
                'background-color': 'white',
                'text-align': 'center'
            });
            $text = $indicator.children( '.loading-indicator-text' ).css({
                'margin-top'        : '20px'
            });

        } else {
            $text = $indicator.children( '.loading-indicator-text' ).css({
                margin              : '12px 0px 0px 10px',
                opacity             : '0.85',
                color               : 'grey'
            });
            $text.children( '.loading-indicator-message' ).css({
                margin          : '0px 8px 0px 0px',
                'font-style'    : 'italic'
            });
        }
        return $indicator;
    }

    self.show = function( msg, speed, callback ){
        msg = msg || 'loading...';
        speed = speed || 'fast';
        // remove previous
        $where.parent().find( '.loading-indicator' ).remove();
        // since position is fixed - we insert as sibling
        self.$indicator = render().insertBefore( $where );
        self.message( msg );
        self.$indicator.fadeIn( speed, callback );
        return self;
    };

    self.message = function( msg ){
        self.$indicator.find( 'i' ).text( msg );
    };

    self.hide = function( speed, callback ){
        speed = speed || 'fast';
        if( self.$indicator && self.$indicator.size() ){
            self.$indicator.fadeOut( speed, function(){
                self.$indicator.remove();
                if( callback ){ callback(); }
            });
        } else {
            if( callback ){ callback(); }
        }
        return self;
    };
    return self;
}

//==============================================================================
(function(){
    /** searchInput: (jQuery plugin)
     *      Creates a search input, a clear button, and loading indicator
     *      within the selected node.
     *
     *      When the user either presses return or enters some minimal number
     *      of characters, a callback is called. Pressing ESC when the input
     *      is focused will clear the input and call a separate callback.
     */
    var _l = window._l || function( s ){ return s; };

    // contructor
    function searchInput( parentNode, options ){
//TODO: consolidate with tool menu functionality, use there
        var KEYCODE_ESC     = 27,
            KEYCODE_RETURN  = 13,
            $parentNode     = $( parentNode ),
            firstSearch     = true,
            defaults = {
                initialVal      : '',
                name            : 'search',
                placeholder     : 'search',
                classes         : '',
                onclear         : function(){},
                onfirstsearch   : null,
                onsearch        : function( inputVal ){},
                minSearchLen    : 0,
                escWillClear    : true,
                oninit          : function(){}
            };

        // .................................................................... input rendering and events
        // visually clear the search, trigger an event, and call the callback
        function clearSearchInput( event ){
            var $input = $( this ).parent().children( 'input' );
            //console.debug( this, 'clear', $input );
            $input.focus().val( '' ).trigger( 'clear:searchInput' );
            options.onclear();
        }

        // search for searchTerms, trigger an event, call the appropo callback (based on whether this is the first)
        function search( event, searchTerms ){
            //console.debug( this, 'searching', searchTerms );
            $( this ).trigger( 'search:searchInput', searchTerms );
            if( typeof options.onfirstsearch === 'function' && firstSearch ){
                firstSearch = false;
                options.onfirstsearch( searchTerms );
            } else {
                options.onsearch( searchTerms );
            }
        }

        // .................................................................... input rendering and events
        function inputTemplate(){
            // class search-query is bootstrap 2.3 style that now lives in base.less
            return [ '<input type="text" name="', options.name, '" placeholder="', options.placeholder, '" ',
                            'class="search-query ', options.classes, '" ', '/>' ].join( '' );
        }

        // the search input that responds to keyboard events and displays the search value
        function $input(){
            return $( inputTemplate() )
                // select all text on a focus
                .focus( function( event ){
                    $( this ).select();
                })
                // attach behaviors to esc, return if desired, search on some min len string
                .keyup( function( event ){
                    event.preventDefault();
                    event.stopPropagation();
//TODO: doesn't work
                    if( !$( this ).val() ){ $( this ).blur(); }

                    // esc key will clear if desired
                    if( event.which === KEYCODE_ESC && options.escWillClear ){
                        clearSearchInput.call( this, event );

                    } else {
                        var searchTerms = $( this ).val();
                        // return key or the search string len > minSearchLen (if not 0) triggers search
                        if( ( event.which === KEYCODE_RETURN )
                        ||  ( options.minSearchLen && searchTerms.length >= options.minSearchLen ) ){
                            search.call( this, event, searchTerms );
                        } else if( !searchTerms.length ){
                            clearSearchInput.call( this, event );
                        }
                    }
                })
                .on( 'change', function( event ){
                    search.call( this, event, $( this ).val() );
                })
                .val( options.initialVal );
        }

        // .................................................................... clear button rendering and events
        // a button for clearing the search bar, placed on the right hand side
        function $clearBtn(){
            return $([ '<span class="search-clear fa fa-times-circle" ',
                             'title="', _l( 'clear search (esc)' ), '"></span>' ].join('') )
            .tooltip({ placement: 'bottom' })
            .click( function( event ){
                clearSearchInput.call( this, event );
            });
        }

        // .................................................................... loadingIndicator rendering
        // a button for clearing the search bar, placed on the right hand side
        function $loadingIndicator(){
            return $([ '<span class="search-loading fa fa-spinner fa-spin" ',
                             'title="', _l( 'loading...' ), '"></span>' ].join('') )
                .hide().tooltip({ placement: 'bottom' });
        }

        // .................................................................... commands
        // visually swap the load, clear buttons
        function toggleLoadingIndicator(){
            $parentNode.find( '.search-loading' ).toggle();
            $parentNode.find( '.search-clear' ).toggle();
        }

        // .................................................................... init
        // string command (not constructor)
        if( jQuery.type( options ) === 'string' ){
            if( options === 'toggle-loading' ){
                toggleLoadingIndicator();
            }
            return $parentNode;
        }

        // initial render
        if( jQuery.type( options ) === 'object' ){
            options = jQuery.extend( true, {}, defaults, options );
        }
        //NOTE: prepended
        return $parentNode.addClass( 'search-input' ).prepend([ $input(), $clearBtn(), $loadingIndicator() ]);
    }

    // as jq plugin
    jQuery.fn.extend({
        searchInput : function $searchInput( options ){
            return this.each( function(){
                return searchInput( this, options );
            });
        }
    });
}());


//==============================================================================
(function(){
    /** Multi 'mode' button (or any element really) that changes the html
     *      contents of itself when clicked. Pass in an ordered list of
     *      objects with 'html' and (optional) onclick functions.
     *
     *      When clicked in a particular node, the onclick function will
     *      be called (with the element as this) and the element will
     *      switch to the next mode, replacing its html content with
     *      that mode's html.
     *
     *      If there is no next mode, the element will switch back to
     *      the first mode.
     * @example:
     *     $( '.myElement' ).modeButton({
     *         modes : [
     *             {
     *                 mode: 'bler',
     *                 html: '<h5>Bler</h5>',
     *                 onclick : function(){
     *                     $( 'body' ).css( 'background-color', 'red' );
     *                 }
     *             },
     *             {
     *                 mode: 'bloo',
     *                 html: '<h4>Bloo</h4>',
     *                 onclick : function(){
     *                     $( 'body' ).css( 'background-color', 'blue' );
     *                 }
     *             },
     *             {
     *                 mode: 'blah',
     *                 html: '<h3>Blah</h3>',
     *                 onclick : function(){
     *                     $( 'body' ).css( 'background-color', 'grey' );
     *                 }
     *             },
     *         ]
     *     });
     *     $( '.myElement' ).modeButton( 'callModeFn', 'bler' );
     */
    /** constructor */
    function ModeButton( element, options ){
		this.currModeIndex = 0;
		return this._init( element, options );
    }

    /** html5 data key to store this object inside an element */
	ModeButton.prototype.DATA_KEY = 'mode-button';
    /** default options */
	ModeButton.prototype.defaults = {
        switchModesOnClick : true
	};

    // ---- private interface
    /** set up options, intial mode, and the click handler */
	ModeButton.prototype._init = function _init( element, options ){
        //console.debug( 'ModeButton._init:', element, options );
		options = options || {};
		this.$element = $( element );
		this.options = jQuery.extend( true, {}, this.defaults, options );
        if( !options.modes ){
            throw new Error( 'ModeButton requires a "modes" array' );
        }

		var modeButton = this;
		this.$element.click( function _ModeButtonClick( event ){
			// call the curr mode fn
			modeButton.callModeFn();
			// inc the curr mode index
			if( modeButton.options.switchModesOnClick ){ modeButton._incModeIndex(); }
			// set the element html
			$( this ).html( modeButton.options.modes[ modeButton.currModeIndex ].html );
		});
		return this.reset();
	};
    /** increment the mode index to the next in the array, looping back to zero if at the last */
	ModeButton.prototype._incModeIndex = function _incModeIndex(){
		this.currModeIndex += 1;
		if( this.currModeIndex >= this.options.modes.length ){
			this.currModeIndex = 0;
		}
		return this;
	};
    /** get the mode index in the modes array for the given key (mode name) */
	ModeButton.prototype._getModeIndex = function _getModeIndex( modeKey ){
		for( var i=0; i<this.options.modes.length; i+=1 ){
			if( this.options.modes[ i ].mode === modeKey ){ return i; }
		}
		throw new Error( 'mode not found: ' + modeKey );
	};
    /** set the current mode to the one with the given index and set button html */
	ModeButton.prototype._setModeByIndex = function _setModeByIndex( index ){
        var newMode = this.options.modes[ index ];
        if( !newMode ){
            throw new Error( 'mode index not found: ' + index );
        }
        this.currModeIndex = index;
        if( newMode.html ){
            this.$element.html( newMode.html );
        }
		return this;
	};

    // ---- public interface
    /** get the current mode object (not just the mode name) */
	ModeButton.prototype.currentMode = function currentMode(){
		return this.options.modes[ this.currModeIndex ];
	};
    /** return the mode key of the current mode */
	ModeButton.prototype.current = function current(){
        // sugar for returning mode name
		return this.currentMode().mode;
	};
    /** get the mode with the given modeKey or the current mode if modeKey is undefined */
	ModeButton.prototype.getMode = function getMode( modeKey ){
		if( !modeKey ){ return this.currentMode(); }
		return this.options.modes[( this._getModeIndex( modeKey ) )];
	};
    /** T/F if the button has the given mode */
	ModeButton.prototype.hasMode = function hasMode( modeKey ){
        try {
            return !!this.getMode( modeKey );
        } catch( err ){}
        return false;
	};
    /** set the current mode to the mode with the given name */
	ModeButton.prototype.setMode = function setMode( modeKey ){
        return this._setModeByIndex( this._getModeIndex( modeKey ) );
	};
    /** reset to the initial mode */
	ModeButton.prototype.reset = function reset(){
		this.currModeIndex = 0;
		if( this.options.initialMode ){
			this.currModeIndex = this._getModeIndex( this.options.initialMode );
		}
        return this._setModeByIndex( this.currModeIndex );
	};
    /** manually call the click handler of the given mode */
	ModeButton.prototype.callModeFn = function callModeFn( modeKey ){
		var modeFn = this.getMode( modeKey ).onclick;
		if( modeFn && jQuery.type( modeFn === 'function' ) ){
            // call with the element as context (std jquery pattern)
			return modeFn.call( this.$element.get(0) );
		}
		return undefined;
	};

    // as jq plugin
    jQuery.fn.extend({
        modeButton : function $modeButton( options ){
            if( !this.size() ){ return this; }
            
            //TODO: does map still work with jq multi selection (i.e. $( '.class-for-many-btns' ).modeButton)?
            if( jQuery.type( options ) === 'object' ){
                return this.map( function(){
                    var $this = $( this );
                    $this.data( 'mode-button', new ModeButton( $this, options ) );
                    return this;
                });
            }

            var $first = $( this[0] ),
                button = $first.data( 'mode-button' );

            if( !button ){
                throw new Error( 'modeButton needs an options object or string name of a function' );
            }

            if( button && jQuery.type( options ) === 'string' ){
                var fnName = options;
                if( button && jQuery.type( button[ fnName ] ) === 'function' ){
                    return button[ fnName ].apply( button, jQuery.makeArray( arguments ).slice( 1 ) );
                }
            }
            return button;
        }
    });
}());


//==============================================================================
/**
 *  Template function that produces a bootstrap dropdown to replace the
 *  vanilla HTML select input. Pass in an array of options and an initial selection:
 *  $( '.my-div' ).append( dropDownSelect( [ 'option1', 'option2' ], 'option2' );
 *
 *  When the user changes the selected option a 'change.dropdown-select' event will
 *  fire with both the jq event and the new selection text as arguments.
 *
 *  Get the currently selected choice using:
 *  var userChoice = $( '.my-div .dropdown-select .dropdown-select-selected' ).text();
 *
 */
function dropDownSelect( options, selected ){
    // replacement for vanilla select element using bootstrap dropdowns instead
    selected = selected || (( !_.isEmpty( options ) )?( options[0] ):( '' ));
    var $select = $([
            '<div class="dropdown-select btn-group">',
                '<button type="button" class="btn btn-default">',
                    '<span class="dropdown-select-selected">' + selected + '</span>',
                '</button>',
            '</div>'
        ].join( '\n' ));

    // if there's only one option, do not style/create as buttons, dropdown - use simple span
    // otherwise, a dropdown displaying the current selection
    if( options && options.length > 1 ){
        $select.find( 'button' )
            .addClass( 'dropdown-toggle' ).attr( 'data-toggle', 'dropdown' )
            .append( ' <span class="caret"></span>' );
        $select.append([
            '<ul class="dropdown-menu" role="menu">',
                _.map( options, function( option ){
                    return [
                        '<li><a href="javascript:void(0)">', option, '</a></li>'
                    ].join( '' );
                }).join( '\n' ),
            '</ul>'
        ].join( '\n' ));
    }

    // trigger 'change.dropdown-select' when a new selection is made using the dropdown
    function selectThis( event ){
        var $this = $( this ),
            $select = $this.parents( '.dropdown-select' ),
            newSelection = $this.text();
        $select.find( '.dropdown-select-selected' ).text( newSelection );
        $select.trigger( 'change.dropdown-select', newSelection );
    }

    $select.find( 'a' ).click( selectThis );
    return $select;
}


//==============================================================================
(function(){
    /**
     *  Creates a three part bootstrap button group (key, op, value) meant to
     *  allow the user control of filters (e.g. { key: 'name', op: 'contains', value: 'my_history' })
     *
     *  Each field uses a dropDownSelect (from ui.js) to allow selection
     *  (with the 'value' field appearing as an input when set to do so).
     *
     *  Any change or update in any of the fields will trigger a 'change.filter-control'
     *  event which will be passed an object containing those fields (as the example above).
     *
     *  Pass in an array of possible filter objects to control what the user can select.
     *  Each filter object should have:
     *      key : generally the attribute name on which to filter something
     *      ops : an array of 1 or more filter operations (e.g. [ 'is', '<', 'contains', '!=' ])
     *      values (optional) : an array of possible values for the filter (e.g. [ 'true', 'false' ])
     *  @example:
     *  $( '.my-div' ).filterControl({
     *      filters : [
     *          { key: 'name',    ops: [ 'is exactly', 'contains' ] }
     *          { key: 'deleted', ops: [ 'is' ], values: [ 'true', 'false' ] }
     *      ]
     *  });
     *  // after initialization, you can prog. get the current value using:
     *  $( '.my-div' ).filterControl( 'val' )
     *
     */
    function FilterControl( element, options ){
		return this.init( element, options );
    }
    /** the data key that this object will be stored under in the DOM element */
	FilterControl.prototype.DATA_KEY = 'filter-control';

    /** parses options, sets up instance vars, and does initial render */
	FilterControl.prototype.init = function _init( element, options ){
		options = options || { filters: [] };
		this.$element = $( element ).addClass( 'filter-control btn-group' );
		this.options = jQuery.extend( true, {}, this.defaults, options );

        this.currFilter = this.options.filters[0];
		return this.render();
	};

    /** render (or re-render) the controls on the element */
	FilterControl.prototype.render = function _render(){
        this.$element.empty()
            .append([ this._renderKeySelect(), this._renderOpSelect(), this._renderValueInput() ]);
        return this;
    };

    /** render the key dropDownSelect, bind a change event to it, and return it */
	FilterControl.prototype._renderKeySelect = function __renderKeySelect(){
        var filterControl = this;
        var keys = this.options.filters.map( function( filter ){
            return filter.key;
        });
        this.$keySelect = dropDownSelect( keys, this.currFilter.key )
            .addClass( 'filter-control-key' )
            .on( 'change.dropdown-select', function( event, selection ){
                filterControl.currFilter = _.findWhere( filterControl.options.filters, { key: selection });
                // when the filter/key changes, re-render the control entirely
                filterControl.render()._triggerChange();
            });
        return this.$keySelect;
    };

    /** render the op dropDownSelect, bind a change event to it, and return it */
	FilterControl.prototype._renderOpSelect = function __renderOpSelect(){
        var filterControl = this,
            ops = this.currFilter.ops;
        //TODO: search for currOp in avail. ops: use that for selected if there; otherwise: first op
        this.$opSelect = dropDownSelect( ops, ops[0] )
            .addClass( 'filter-control-op' )
            .on( 'change.dropdown-select', function( event, selection ){
                filterControl._triggerChange();
            });
        return this.$opSelect;
    };

    /** render the value control, bind a change event to it, and return it */
	FilterControl.prototype._renderValueInput = function __renderValueInput(){
        var filterControl = this;
        // if a values attribute is prov. on the filter - make this a dropdown; otherwise, use an input
        if( this.currFilter.values ){
            this.$valueSelect = dropDownSelect( this.currFilter.values, this.currFilter.values[0] )
                .on( 'change.dropdown-select', function( event, selection ){
                    filterControl._triggerChange();
                });
        } else {
            //TODO: allow setting a value type (mainly for which html5 input to use: range, number, etc.)
            this.$valueSelect = $( '<input/>' ).addClass( 'form-control' )
                .on( 'change', function( event, value ){
                    filterControl._triggerChange();
                });
        }
        this.$valueSelect.addClass( 'filter-control-value' );
        return this.$valueSelect;
    };

    /** return the current state/setting for the filter as a three key object: key, op, value */
	FilterControl.prototype.val = function _val(){
        var key = this.$element.find( '.filter-control-key .dropdown-select-selected' ).text(),
            op  = this.$element.find( '.filter-control-op .dropdown-select-selected'  ).text(),
            // handle either a dropdown or plain input
            $value = this.$element.find( '.filter-control-value' ),
            value = ( $value.hasClass( 'dropdown-select' ) )?( $value.find( '.dropdown-select-selected' ).text() )
                                                            :( $value.val() );
        return { key: key, op: op, value: value };
    };

    // single point of change for change event
	FilterControl.prototype._triggerChange = function __triggerChange(){
        this.$element.trigger( 'change.filter-control', this.val() );
    };


    // as jq plugin
    jQuery.fn.extend({
        filterControl : function $filterControl( options ){
			var nonOptionsArgs = jQuery.makeArray( arguments ).slice( 1 );
            return this.map( function(){
				var $this = $( this ),
					data = $this.data( FilterControl.prototype.DATA_KEY );

				if( jQuery.type( options ) === 'object' ){
					data = new FilterControl( $this, options );
					$this.data( FilterControl.prototype.DATA_KEY, data );
				}
				if( data && jQuery.type( options ) === 'string' ){
					var fn = data[ options ];
					if( jQuery.type( fn ) === 'function' ){
						return fn.apply( data, nonOptionsArgs );
					}
				}
				return this;
            });
        }
    });
}());
