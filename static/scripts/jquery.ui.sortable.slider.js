/*!
 * jQuery UI 1.8.5
 *
 * Copyright 2010, AUTHORS.txt (http://jqueryui.com/about)
 * Dual licensed under the MIT or GPL Version 2 licenses.
 * http://jquery.org/license
 *
 * http://docs.jquery.com/UI
 */
(function( $, undefined ) {

// prevent duplicate loading
// this is only a problem because we proxy existing functions
// and we don't want to double proxy them
$.ui = $.ui || {};
if ( $.ui.version ) {
	return;
}

$.extend( $.ui, {
	version: "1.8.5",

	keyCode: {
		ALT: 18,
		BACKSPACE: 8,
		CAPS_LOCK: 20,
		COMMA: 188,
		COMMAND: 91,
		COMMAND_LEFT: 91, // COMMAND
		COMMAND_RIGHT: 93,
		CONTROL: 17,
		DELETE: 46,
		DOWN: 40,
		END: 35,
		ENTER: 13,
		ESCAPE: 27,
		HOME: 36,
		INSERT: 45,
		LEFT: 37,
		MENU: 93, // COMMAND_RIGHT
		NUMPAD_ADD: 107,
		NUMPAD_DECIMAL: 110,
		NUMPAD_DIVIDE: 111,
		NUMPAD_ENTER: 108,
		NUMPAD_MULTIPLY: 106,
		NUMPAD_SUBTRACT: 109,
		PAGE_DOWN: 34,
		PAGE_UP: 33,
		PERIOD: 190,
		RIGHT: 39,
		SHIFT: 16,
		SPACE: 32,
		TAB: 9,
		UP: 38,
		WINDOWS: 91 // COMMAND
	}
});

// plugins
$.fn.extend({
	_focus: $.fn.focus,
	focus: function( delay, fn ) {
		return typeof delay === "number" ?
			this.each(function() {
				var elem = this;
				setTimeout(function() {
					$( elem ).focus();
					if ( fn ) {
						fn.call( elem );
					}
				}, delay );
			}) :
			this._focus.apply( this, arguments );
	},

	scrollParent: function() {
		var scrollParent;
		if (($.browser.msie && (/(static|relative)/).test(this.css('position'))) || (/absolute/).test(this.css('position'))) {
			scrollParent = this.parents().filter(function() {
				return (/(relative|absolute|fixed)/).test($.curCSS(this,'position',1)) && (/(auto|scroll)/).test($.curCSS(this,'overflow',1)+$.curCSS(this,'overflow-y',1)+$.curCSS(this,'overflow-x',1));
			}).eq(0);
		} else {
			scrollParent = this.parents().filter(function() {
				return (/(auto|scroll)/).test($.curCSS(this,'overflow',1)+$.curCSS(this,'overflow-y',1)+$.curCSS(this,'overflow-x',1));
			}).eq(0);
		}

		return (/fixed/).test(this.css('position')) || !scrollParent.length ? $(document) : scrollParent;
	},

	zIndex: function( zIndex ) {
		if ( zIndex !== undefined ) {
			return this.css( "zIndex", zIndex );
		}

		if ( this.length ) {
			var elem = $( this[ 0 ] ), position, value;
			while ( elem.length && elem[ 0 ] !== document ) {
				// Ignore z-index if position is set to a value where z-index is ignored by the browser
				// This makes behavior of this function consistent across browsers
				// WebKit always returns auto if the element is positioned
				position = elem.css( "position" );
				if ( position === "absolute" || position === "relative" || position === "fixed" ) {
					// IE returns 0 when zIndex is not specified
					// other browsers return a string
					// we ignore the case of nested elements with an explicit value of 0
					// <div style="z-index: -10;"><div style="z-index: 0;"></div></div>
					value = parseInt( elem.css( "zIndex" ) );
					if ( !isNaN( value ) && value != 0 ) {
						return value;
					}
				}
				elem = elem.parent();
			}
		}

		return 0;
	},
	
	disableSelection: function() {
		return this.bind(
			"mousedown.ui-disableSelection selectstart.ui-disableSelection",
			function( event ) {
				event.preventDefault();
			});
	},

	enableSelection: function() {
		return this.unbind( ".ui-disableSelection" );
	}
});

$.each( [ "Width", "Height" ], function( i, name ) {
	var side = name === "Width" ? [ "Left", "Right" ] : [ "Top", "Bottom" ],
		type = name.toLowerCase(),
		orig = {
			innerWidth: $.fn.innerWidth,
			innerHeight: $.fn.innerHeight,
			outerWidth: $.fn.outerWidth,
			outerHeight: $.fn.outerHeight
		};

	function reduce( elem, size, border, margin ) {
		$.each( side, function() {
			size -= parseFloat( $.curCSS( elem, "padding" + this, true) ) || 0;
			if ( border ) {
				size -= parseFloat( $.curCSS( elem, "border" + this + "Width", true) ) || 0;
			}
			if ( margin ) {
				size -= parseFloat( $.curCSS( elem, "margin" + this, true) ) || 0;
			}
		});
		return size;
	}

	$.fn[ "inner" + name ] = function( size ) {
		if ( size === undefined ) {
			return orig[ "inner" + name ].call( this );
		}

		return this.each(function() {
			$.style( this, type, reduce( this, size ) + "px" );
		});
	};

	$.fn[ "outer" + name] = function( size, margin ) {
		if ( typeof size !== "number" ) {
			return orig[ "outer" + name ].call( this, size );
		}

		return this.each(function() {
			$.style( this, type, reduce( this, size, true, margin ) + "px" );
		});
	};
});

// selectors
function visible( element ) {
	return !$( element ).parents().andSelf().filter(function() {
		return $.curCSS( this, "visibility" ) === "hidden" ||
			$.expr.filters.hidden( this );
	}).length;
}

$.extend( $.expr[ ":" ], {
	data: function( elem, i, match ) {
		return !!$.data( elem, match[ 3 ] );
	},

	focusable: function( element ) {
		var nodeName = element.nodeName.toLowerCase(),
			tabIndex = $.attr( element, "tabindex" );
		if ( "area" === nodeName ) {
			var map = element.parentNode,
				mapName = map.name,
				img;
			if ( !element.href || !mapName || map.nodeName.toLowerCase() !== "map" ) {
				return false;
			}
			img = $( "img[usemap=#" + mapName + "]" )[0];
			return !!img && visible( img );
		}
		return ( /input|select|textarea|button|object/.test( nodeName )
			? !element.disabled
			: "a" == nodeName
				? element.href || !isNaN( tabIndex )
				: !isNaN( tabIndex ))
			// the element and all of its ancestors must be visible
			&& visible( element );
	},

	tabbable: function( element ) {
		var tabIndex = $.attr( element, "tabindex" );
		return ( isNaN( tabIndex ) || tabIndex >= 0 ) && $( element ).is( ":focusable" );
	}
});

// support
$(function() {
	var div = document.createElement( "div" ),
		body = document.body;

	$.extend( div.style, {
		minHeight: "100px",
		height: "auto",
		padding: 0,
		borderWidth: 0
	});

	$.support.minHeight = body.appendChild( div ).offsetHeight === 100;
	// set display to none to avoid a layout bug in IE
	// http://dev.jquery.com/ticket/4014
	body.removeChild( div ).style.display = "none";
});





// deprecated
$.extend( $.ui, {
	// $.ui.plugin is deprecated.  Use the proxy pattern instead.
	plugin: {
		add: function( module, option, set ) {
			var proto = $.ui[ module ].prototype;
			for ( var i in set ) {
				proto.plugins[ i ] = proto.plugins[ i ] || [];
				proto.plugins[ i ].push( [ option, set[ i ] ] );
			}
		},
		call: function( instance, name, args ) {
			var set = instance.plugins[ name ];
			if ( !set || !instance.element[ 0 ].parentNode ) {
				return;
			}
	
			for ( var i = 0; i < set.length; i++ ) {
				if ( instance.options[ set[ i ][ 0 ] ] ) {
					set[ i ][ 1 ].apply( instance.element, args );
				}
			}
		}
	},
	
	// will be deprecated when we switch to jQuery 1.4 - use jQuery.contains()
	contains: function( a, b ) {
		return document.compareDocumentPosition ?
			a.compareDocumentPosition( b ) & 16 :
			a !== b && a.contains( b );
	},
	
	// only used by resizable
	hasScroll: function( el, a ) {
	
		//If overflow is hidden, the element might have extra content, but the user wants to hide it
		if ( $( el ).css( "overflow" ) === "hidden") {
			return false;
		}
	
		var scroll = ( a && a === "left" ) ? "scrollLeft" : "scrollTop",
			has = false;
	
		if ( el[ scroll ] > 0 ) {
			return true;
		}
	
		// TODO: determine which cases actually cause this to happen
		// if the element doesn't have the scroll set, see if it's possible to
		// set the scroll
		el[ scroll ] = 1;
		has = ( el[ scroll ] > 0 );
		el[ scroll ] = 0;
		return has;
	},
	
	// these are odd functions, fix the API or move into individual plugins
	isOverAxis: function( x, reference, size ) {
		//Determines when x coordinate is over "b" element axis
		return ( x > reference ) && ( x < ( reference + size ) );
	},
	isOver: function( y, x, top, left, height, width ) {
		//Determines when x, y coordinates is over "b" element
		return $.ui.isOverAxis( y, top, height ) && $.ui.isOverAxis( x, left, width );
	}
});

})( jQuery );
/*!
 * jQuery UI Widget 1.8.5
 *
 * Copyright 2010, AUTHORS.txt (http://jqueryui.com/about)
 * Dual licensed under the MIT or GPL Version 2 licenses.
 * http://jquery.org/license
 *
 * http://docs.jquery.com/UI/Widget
 */
(function( $, undefined ) {

// jQuery 1.4+
if ( $.cleanData ) {
	var _cleanData = $.cleanData;
	$.cleanData = function( elems ) {
		for ( var i = 0, elem; (elem = elems[i]) != null; i++ ) {
			$( elem ).triggerHandler( "remove" );
		}
		_cleanData( elems );
	};
} else {
	var _remove = $.fn.remove;
	$.fn.remove = function( selector, keepData ) {
		return this.each(function() {
			if ( !keepData ) {
				if ( !selector || $.filter( selector, [ this ] ).length ) {
					$( "*", this ).add( [ this ] ).each(function() {
						$( this ).triggerHandler( "remove" );
					});
				}
			}
			return _remove.call( $(this), selector, keepData );
		});
	};
}

$.widget = function( name, base, prototype ) {
	var namespace = name.split( "." )[ 0 ],
		fullName;
	name = name.split( "." )[ 1 ];
	fullName = namespace + "-" + name;

	if ( !prototype ) {
		prototype = base;
		base = $.Widget;
	}

	// create selector for plugin
	$.expr[ ":" ][ fullName ] = function( elem ) {
		return !!$.data( elem, name );
	};

	$[ namespace ] = $[ namespace ] || {};
	$[ namespace ][ name ] = function( options, element ) {
		// allow instantiation without initializing for simple inheritance
		if ( arguments.length ) {
			this._createWidget( options, element );
		}
	};

	var basePrototype = new base();
	// we need to make the options hash a property directly on the new instance
	// otherwise we'll modify the options hash on the prototype that we're
	// inheriting from
//	$.each( basePrototype, function( key, val ) {
//		if ( $.isPlainObject(val) ) {
//			basePrototype[ key ] = $.extend( {}, val );
//		}
//	});
	basePrototype.options = $.extend( true, {}, basePrototype.options );
	$[ namespace ][ name ].prototype = $.extend( true, basePrototype, {
		namespace: namespace,
		widgetName: name,
		widgetEventPrefix: $[ namespace ][ name ].prototype.widgetEventPrefix || name,
		widgetBaseClass: fullName
	}, prototype );

	$.widget.bridge( name, $[ namespace ][ name ] );
};

$.widget.bridge = function( name, object ) {
	$.fn[ name ] = function( options ) {
		var isMethodCall = typeof options === "string",
			args = Array.prototype.slice.call( arguments, 1 ),
			returnValue = this;

		// allow multiple hashes to be passed on init
		options = !isMethodCall && args.length ?
			$.extend.apply( null, [ true, options ].concat(args) ) :
			options;

		// prevent calls to internal methods
		if ( isMethodCall && options.substring( 0, 1 ) === "_" ) {
			return returnValue;
		}

		if ( isMethodCall ) {
			this.each(function() {
				var instance = $.data( this, name );
				if ( !instance ) {
					throw "cannot call methods on " + name + " prior to initialization; " +
						"attempted to call method '" + options + "'";
				}
				if ( !$.isFunction( instance[options] ) ) {
					throw "no such method '" + options + "' for " + name + " widget instance";
				}
				var methodValue = instance[ options ].apply( instance, args );
				if ( methodValue !== instance && methodValue !== undefined ) {
					returnValue = methodValue;
					return false;
				}
			});
		} else {
			this.each(function() {
				var instance = $.data( this, name );
				if ( instance ) {
					instance.option( options || {} )._init();
				} else {
					$.data( this, name, new object( options, this ) );
				}
			});
		}

		return returnValue;
	};
};

$.Widget = function( options, element ) {
	// allow instantiation without initializing for simple inheritance
	if ( arguments.length ) {
		this._createWidget( options, element );
	}
};

$.Widget.prototype = {
	widgetName: "widget",
	widgetEventPrefix: "",
	options: {
		disabled: false
	},
	_createWidget: function( options, element ) {
		// $.widget.bridge stores the plugin instance, but we do it anyway
		// so that it's stored even before the _create function runs
		$.data( element, this.widgetName, this );
		this.element = $( element );
		this.options = $.extend( true, {},
			this.options,
			$.metadata && $.metadata.get( element )[ this.widgetName ],
			options );

		var self = this;
		this.element.bind( "remove." + this.widgetName, function() {
			self.destroy();
		});

		this._create();
		this._init();
	},
	_create: function() {},
	_init: function() {},

	destroy: function() {
		this.element
			.unbind( "." + this.widgetName )
			.removeData( this.widgetName );
		this.widget()
			.unbind( "." + this.widgetName )
			.removeAttr( "aria-disabled" )
			.removeClass(
				this.widgetBaseClass + "-disabled " +
				"ui-state-disabled" );
	},

	widget: function() {
		return this.element;
	},

	option: function( key, value ) {
		var options = key,
			self = this;

		if ( arguments.length === 0 ) {
			// don't return a reference to the internal hash
			return $.extend( {}, self.options );
		}

		if  (typeof key === "string" ) {
			if ( value === undefined ) {
				return this.options[ key ];
			}
			options = {};
			options[ key ] = value;
		}

		$.each( options, function( key, value ) {
			self._setOption( key, value );
		});

		return self;
	},
	_setOption: function( key, value ) {
		this.options[ key ] = value;

		if ( key === "disabled" ) {
			this.widget()
				[ value ? "addClass" : "removeClass"](
					this.widgetBaseClass + "-disabled" + " " +
					"ui-state-disabled" )
				.attr( "aria-disabled", value );
		}

		return this;
	},

	enable: function() {
		return this._setOption( "disabled", false );
	},
	disable: function() {
		return this._setOption( "disabled", true );
	},

	_trigger: function( type, event, data ) {
		var callback = this.options[ type ];

		event = $.Event( event );
		event.type = ( type === this.widgetEventPrefix ?
			type :
			this.widgetEventPrefix + type ).toLowerCase();
		data = data || {};

		// copy original event properties over to the new event
		// this would happen if we could call $.event.fix instead of $.Event
		// but we don't have a way to force an event to be fixed multiple times
		if ( event.originalEvent ) {
			for ( var i = $.event.props.length, prop; i; ) {
				prop = $.event.props[ --i ];
				event[ prop ] = event.originalEvent[ prop ];
			}
		}

		this.element.trigger( event, data );

		return !( $.isFunction(callback) &&
			callback.call( this.element[0], event, data ) === false ||
			event.isDefaultPrevented() );
	}
};

})( jQuery );
/*!
 * jQuery UI Mouse 1.8.5
 *
 * Copyright 2010, AUTHORS.txt (http://jqueryui.com/about)
 * Dual licensed under the MIT or GPL Version 2 licenses.
 * http://jquery.org/license
 *
 * http://docs.jquery.com/UI/Mouse
 *
 * Depends:
 *	jquery.ui.widget.js
 */
(function( $, undefined ) {

$.widget("ui.mouse", {
	options: {
		cancel: ':input,option',
		distance: 1,
		delay: 0
	},
	_mouseInit: function() {
		var self = this;

		this.element
			.bind('mousedown.'+this.widgetName, function(event) {
				return self._mouseDown(event);
			})
			.bind('click.'+this.widgetName, function(event) {
				if(self._preventClickEvent) {
					self._preventClickEvent = false;
					event.stopImmediatePropagation();
					return false;
				}
			});

		this.started = false;
	},

	// TODO: make sure destroying one instance of mouse doesn't mess with
	// other instances of mouse
	_mouseDestroy: function() {
		this.element.unbind('.'+this.widgetName);
	},

	_mouseDown: function(event) {
		// don't let more than one widget handle mouseStart
		// TODO: figure out why we have to use originalEvent
		event.originalEvent = event.originalEvent || {};
		if (event.originalEvent.mouseHandled) { return; }

		// we may have missed mouseup (out of window)
		(this._mouseStarted && this._mouseUp(event));

		this._mouseDownEvent = event;

		var self = this,
			btnIsLeft = (event.which == 1),
			elIsCancel = (typeof this.options.cancel == "string" ? $(event.target).parents().add(event.target).filter(this.options.cancel).length : false);
		if (!btnIsLeft || elIsCancel || !this._mouseCapture(event)) {
			return true;
		}

		this.mouseDelayMet = !this.options.delay;
		if (!this.mouseDelayMet) {
			this._mouseDelayTimer = setTimeout(function() {
				self.mouseDelayMet = true;
			}, this.options.delay);
		}

		if (this._mouseDistanceMet(event) && this._mouseDelayMet(event)) {
			this._mouseStarted = (this._mouseStart(event) !== false);
			if (!this._mouseStarted) {
				event.preventDefault();
				return true;
			}
		}

		// these delegates are required to keep context
		this._mouseMoveDelegate = function(event) {
			return self._mouseMove(event);
		};
		this._mouseUpDelegate = function(event) {
			return self._mouseUp(event);
		};
		$(document)
			.bind('mousemove.'+this.widgetName, this._mouseMoveDelegate)
			.bind('mouseup.'+this.widgetName, this._mouseUpDelegate);

		// preventDefault() is used to prevent the selection of text here -
		// however, in Safari, this causes select boxes not to be selectable
		// anymore, so this fix is needed
		($.browser.safari || event.preventDefault());

		event.originalEvent.mouseHandled = true;
		return true;
	},

	_mouseMove: function(event) {
		// IE mouseup check - mouseup happened when mouse was out of window
		if ($.browser.msie && !event.button) {
			return this._mouseUp(event);
		}

		if (this._mouseStarted) {
			this._mouseDrag(event);
			return event.preventDefault();
		}

		if (this._mouseDistanceMet(event) && this._mouseDelayMet(event)) {
			this._mouseStarted =
				(this._mouseStart(this._mouseDownEvent, event) !== false);
			(this._mouseStarted ? this._mouseDrag(event) : this._mouseUp(event));
		}

		return !this._mouseStarted;
	},

	_mouseUp: function(event) {
		$(document)
			.unbind('mousemove.'+this.widgetName, this._mouseMoveDelegate)
			.unbind('mouseup.'+this.widgetName, this._mouseUpDelegate);

		if (this._mouseStarted) {
			this._mouseStarted = false;
			this._preventClickEvent = (event.target == this._mouseDownEvent.target);
			this._mouseStop(event);
		}

		return false;
	},

	_mouseDistanceMet: function(event) {
		return (Math.max(
				Math.abs(this._mouseDownEvent.pageX - event.pageX),
				Math.abs(this._mouseDownEvent.pageY - event.pageY)
			) >= this.options.distance
		);
	},

	_mouseDelayMet: function(event) {
		return this.mouseDelayMet;
	},

	// These are placeholder methods, to be overriden by extending plugin
	_mouseStart: function(event) {},
	_mouseDrag: function(event) {},
	_mouseStop: function(event) {},
	_mouseCapture: function(event) { return true; }
});

})(jQuery);
/*
 * jQuery UI Sortable 1.8.5
 *
 * Copyright 2010, AUTHORS.txt (http://jqueryui.com/about)
 * Dual licensed under the MIT or GPL Version 2 licenses.
 * http://jquery.org/license
 *
 * http://docs.jquery.com/UI/Sortables
 *
 * Depends:
 *	jquery.ui.core.js
 *	jquery.ui.mouse.js
 *	jquery.ui.widget.js
 */
(function( $, undefined ) {

$.widget("ui.sortable", $.ui.mouse, {
	widgetEventPrefix: "sort",
	options: {
		appendTo: "parent",
		axis: false,
		connectWith: false,
		containment: false,
		cursor: 'auto',
		cursorAt: false,
		dropOnEmpty: true,
		forcePlaceholderSize: false,
		forceHelperSize: false,
		grid: false,
		handle: false,
		helper: "original",
		items: '> *',
		opacity: false,
		placeholder: false,
		revert: false,
		scroll: true,
		scrollSensitivity: 20,
		scrollSpeed: 20,
		scope: "default",
		tolerance: "intersect",
		zIndex: 1000
	},
	_create: function() {

		var o = this.options;
		this.containerCache = {};
		this.element.addClass("ui-sortable");

		//Get the items
		this.refresh();

		//Let's determine if the items are floating
		this.floating = this.items.length ? (/left|right/).test(this.items[0].item.css('float')) : false;

		//Let's determine the parent's offset
		this.offset = this.element.offset();

		//Initialize mouse events for interaction
		this._mouseInit();

	},

	destroy: function() {
		this.element
			.removeClass("ui-sortable ui-sortable-disabled")
			.removeData("sortable")
			.unbind(".sortable");
		this._mouseDestroy();

		for ( var i = this.items.length - 1; i >= 0; i-- )
			this.items[i].item.removeData("sortable-item");

		return this;
	},

	_setOption: function(key, value){
		if ( key === "disabled" ) {
			this.options[ key ] = value;
	
			this.widget()
				[ value ? "addClass" : "removeClass"]( "ui-sortable-disabled" );
		} else {
			// Don't call widget base _setOption for disable as it adds ui-state-disabled class
			$.Widget.prototype._setOption.apply(this, arguments);
		}
	},

	_mouseCapture: function(event, overrideHandle) {

		if (this.reverting) {
			return false;
		}

		if(this.options.disabled || this.options.type == 'static') return false;

		//We have to refresh the items data once first
		this._refreshItems(event);

		//Find out if the clicked node (or one of its parents) is a actual item in this.items
		var currentItem = null, self = this, nodes = $(event.target).parents().each(function() {
			if($.data(this, 'sortable-item') == self) {
				currentItem = $(this);
				return false;
			}
		});
		if($.data(event.target, 'sortable-item') == self) currentItem = $(event.target);

		if(!currentItem) return false;
		if(this.options.handle && !overrideHandle) {
			var validHandle = false;

			$(this.options.handle, currentItem).find("*").andSelf().each(function() { if(this == event.target) validHandle = true; });
			if(!validHandle) return false;
		}

		this.currentItem = currentItem;
		this._removeCurrentsFromItems();
		return true;

	},

	_mouseStart: function(event, overrideHandle, noActivation) {

		var o = this.options, self = this;
		this.currentContainer = this;

		//We only need to call refreshPositions, because the refreshItems call has been moved to mouseCapture
		this.refreshPositions();

		//Create and append the visible helper
		this.helper = this._createHelper(event);

		//Cache the helper size
		this._cacheHelperProportions();

		/*
		 * - Position generation -
		 * This block generates everything position related - it's the core of draggables.
		 */

		//Cache the margins of the original element
		this._cacheMargins();

		//Get the next scrolling parent
		this.scrollParent = this.helper.scrollParent();

		//The element's absolute position on the page minus margins
		this.offset = this.currentItem.offset();
		this.offset = {
			top: this.offset.top - this.margins.top,
			left: this.offset.left - this.margins.left
		};

		// Only after we got the offset, we can change the helper's position to absolute
		// TODO: Still need to figure out a way to make relative sorting possible
		this.helper.css("position", "absolute");
		this.cssPosition = this.helper.css("position");

		$.extend(this.offset, {
			click: { //Where the click happened, relative to the element
				left: event.pageX - this.offset.left,
				top: event.pageY - this.offset.top
			},
			parent: this._getParentOffset(),
			relative: this._getRelativeOffset() //This is a relative to absolute position minus the actual position calculation - only used for relative positioned helper
		});

		//Generate the original position
		this.originalPosition = this._generatePosition(event);
		this.originalPageX = event.pageX;
		this.originalPageY = event.pageY;

		//Adjust the mouse offset relative to the helper if 'cursorAt' is supplied
		(o.cursorAt && this._adjustOffsetFromHelper(o.cursorAt));

		//Cache the former DOM position
		this.domPosition = { prev: this.currentItem.prev()[0], parent: this.currentItem.parent()[0] };

		//If the helper is not the original, hide the original so it's not playing any role during the drag, won't cause anything bad this way
		if(this.helper[0] != this.currentItem[0]) {
			this.currentItem.hide();
		}

		//Create the placeholder
		this._createPlaceholder();

		//Set a containment if given in the options
		if(o.containment)
			this._setContainment();

		if(o.cursor) { // cursor option
			if ($('body').css("cursor")) this._storedCursor = $('body').css("cursor");
			$('body').css("cursor", o.cursor);
		}

		if(o.opacity) { // opacity option
			if (this.helper.css("opacity")) this._storedOpacity = this.helper.css("opacity");
			this.helper.css("opacity", o.opacity);
		}

		if(o.zIndex) { // zIndex option
			if (this.helper.css("zIndex")) this._storedZIndex = this.helper.css("zIndex");
			this.helper.css("zIndex", o.zIndex);
		}

		//Prepare scrolling
		if(this.scrollParent[0] != document && this.scrollParent[0].tagName != 'HTML')
			this.overflowOffset = this.scrollParent.offset();

		//Call callbacks
		this._trigger("start", event, this._uiHash());

		//Recache the helper size
		if(!this._preserveHelperProportions)
			this._cacheHelperProportions();


		//Post 'activate' events to possible containers
		if(!noActivation) {
			 for (var i = this.containers.length - 1; i >= 0; i--) { this.containers[i]._trigger("activate", event, self._uiHash(this)); }
		}

		//Prepare possible droppables
		if($.ui.ddmanager)
			$.ui.ddmanager.current = this;

		if ($.ui.ddmanager && !o.dropBehaviour)
			$.ui.ddmanager.prepareOffsets(this, event);

		this.dragging = true;

		this.helper.addClass("ui-sortable-helper");
		this._mouseDrag(event); //Execute the drag once - this causes the helper not to be visible before getting its correct position
		return true;

	},

	_mouseDrag: function(event) {

		//Compute the helpers position
		this.position = this._generatePosition(event);
		this.positionAbs = this._convertPositionTo("absolute");

		if (!this.lastPositionAbs) {
			this.lastPositionAbs = this.positionAbs;
		}

		//Do scrolling
		if(this.options.scroll) {
			var o = this.options, scrolled = false;
			if(this.scrollParent[0] != document && this.scrollParent[0].tagName != 'HTML') {

				if((this.overflowOffset.top + this.scrollParent[0].offsetHeight) - event.pageY < o.scrollSensitivity)
					this.scrollParent[0].scrollTop = scrolled = this.scrollParent[0].scrollTop + o.scrollSpeed;
				else if(event.pageY - this.overflowOffset.top < o.scrollSensitivity)
					this.scrollParent[0].scrollTop = scrolled = this.scrollParent[0].scrollTop - o.scrollSpeed;

				if((this.overflowOffset.left + this.scrollParent[0].offsetWidth) - event.pageX < o.scrollSensitivity)
					this.scrollParent[0].scrollLeft = scrolled = this.scrollParent[0].scrollLeft + o.scrollSpeed;
				else if(event.pageX - this.overflowOffset.left < o.scrollSensitivity)
					this.scrollParent[0].scrollLeft = scrolled = this.scrollParent[0].scrollLeft - o.scrollSpeed;

			} else {

				if(event.pageY - $(document).scrollTop() < o.scrollSensitivity)
					scrolled = $(document).scrollTop($(document).scrollTop() - o.scrollSpeed);
				else if($(window).height() - (event.pageY - $(document).scrollTop()) < o.scrollSensitivity)
					scrolled = $(document).scrollTop($(document).scrollTop() + o.scrollSpeed);

				if(event.pageX - $(document).scrollLeft() < o.scrollSensitivity)
					scrolled = $(document).scrollLeft($(document).scrollLeft() - o.scrollSpeed);
				else if($(window).width() - (event.pageX - $(document).scrollLeft()) < o.scrollSensitivity)
					scrolled = $(document).scrollLeft($(document).scrollLeft() + o.scrollSpeed);

			}

			if(scrolled !== false && $.ui.ddmanager && !o.dropBehaviour)
				$.ui.ddmanager.prepareOffsets(this, event);
		}

		//Regenerate the absolute position used for position checks
		this.positionAbs = this._convertPositionTo("absolute");

		//Set the helper position
		if(!this.options.axis || this.options.axis != "y") this.helper[0].style.left = this.position.left+'px';
		if(!this.options.axis || this.options.axis != "x") this.helper[0].style.top = this.position.top+'px';

		//Rearrange
		for (var i = this.items.length - 1; i >= 0; i--) {

			//Cache variables and intersection, continue if no intersection
			var item = this.items[i], itemElement = item.item[0], intersection = this._intersectsWithPointer(item);
			if (!intersection) continue;

			if(itemElement != this.currentItem[0] //cannot intersect with itself
				&&	this.placeholder[intersection == 1 ? "next" : "prev"]()[0] != itemElement //no useless actions that have been done before
				&&	!$.ui.contains(this.placeholder[0], itemElement) //no action if the item moved is the parent of the item checked
				&& (this.options.type == 'semi-dynamic' ? !$.ui.contains(this.element[0], itemElement) : true)
				//&& itemElement.parentNode == this.placeholder[0].parentNode // only rearrange items within the same container
			) {

				this.direction = intersection == 1 ? "down" : "up";

				if (this.options.tolerance == "pointer" || this._intersectsWithSides(item)) {
					this._rearrange(event, item);
				} else {
					break;
				}

				this._trigger("change", event, this._uiHash());
				break;
			}
		}

		//Post events to containers
		this._contactContainers(event);

		//Interconnect with droppables
		if($.ui.ddmanager) $.ui.ddmanager.drag(this, event);

		//Call callbacks
		this._trigger('sort', event, this._uiHash());

		this.lastPositionAbs = this.positionAbs;
		return false;

	},

	_mouseStop: function(event, noPropagation) {

		if(!event) return;

		//If we are using droppables, inform the manager about the drop
		if ($.ui.ddmanager && !this.options.dropBehaviour)
			$.ui.ddmanager.drop(this, event);

		if(this.options.revert) {
			var self = this;
			var cur = self.placeholder.offset();

			self.reverting = true;

			$(this.helper).animate({
				left: cur.left - this.offset.parent.left - self.margins.left + (this.offsetParent[0] == document.body ? 0 : this.offsetParent[0].scrollLeft),
				top: cur.top - this.offset.parent.top - self.margins.top + (this.offsetParent[0] == document.body ? 0 : this.offsetParent[0].scrollTop)
			}, parseInt(this.options.revert, 10) || 500, function() {
				self._clear(event);
			});
		} else {
			this._clear(event, noPropagation);
		}

		return false;

	},

	cancel: function() {

		var self = this;

		if(this.dragging) {

			this._mouseUp();

			if(this.options.helper == "original")
				this.currentItem.css(this._storedCSS).removeClass("ui-sortable-helper");
			else
				this.currentItem.show();

			//Post deactivating events to containers
			for (var i = this.containers.length - 1; i >= 0; i--){
				this.containers[i]._trigger("deactivate", null, self._uiHash(this));
				if(this.containers[i].containerCache.over) {
					this.containers[i]._trigger("out", null, self._uiHash(this));
					this.containers[i].containerCache.over = 0;
				}
			}

		}

		//$(this.placeholder[0]).remove(); would have been the jQuery way - unfortunately, it unbinds ALL events from the original node!
		if(this.placeholder[0].parentNode) this.placeholder[0].parentNode.removeChild(this.placeholder[0]);
		if(this.options.helper != "original" && this.helper && this.helper[0].parentNode) this.helper.remove();

		$.extend(this, {
			helper: null,
			dragging: false,
			reverting: false,
			_noFinalSort: null
		});

		if(this.domPosition.prev) {
			$(this.domPosition.prev).after(this.currentItem);
		} else {
			$(this.domPosition.parent).prepend(this.currentItem);
		}

		return this;

	},

	serialize: function(o) {

		var items = this._getItemsAsjQuery(o && o.connected);
		var str = []; o = o || {};

		$(items).each(function() {
			var res = ($(o.item || this).attr(o.attribute || 'id') || '').match(o.expression || (/(.+)[-=_](.+)/));
			if(res) str.push((o.key || res[1]+'[]')+'='+(o.key && o.expression ? res[1] : res[2]));
		});

		if(!str.length && o.key) {
			str.push(o.key + '=');
		}

		return str.join('&');

	},

	toArray: function(o) {

		var items = this._getItemsAsjQuery(o && o.connected);
		var ret = []; o = o || {};

		items.each(function() { ret.push($(o.item || this).attr(o.attribute || 'id') || ''); });
		return ret;

	},

	/* Be careful with the following core functions */
	_intersectsWith: function(item) {

		var x1 = this.positionAbs.left,
			x2 = x1 + this.helperProportions.width,
			y1 = this.positionAbs.top,
			y2 = y1 + this.helperProportions.height;

		var l = item.left,
			r = l + item.width,
			t = item.top,
			b = t + item.height;

		var dyClick = this.offset.click.top,
			dxClick = this.offset.click.left;

		var isOverElement = (y1 + dyClick) > t && (y1 + dyClick) < b && (x1 + dxClick) > l && (x1 + dxClick) < r;

		if(	   this.options.tolerance == "pointer"
			|| this.options.forcePointerForContainers
			|| (this.options.tolerance != "pointer" && this.helperProportions[this.floating ? 'width' : 'height'] > item[this.floating ? 'width' : 'height'])
		) {
			return isOverElement;
		} else {

			return (l < x1 + (this.helperProportions.width / 2) // Right Half
				&& x2 - (this.helperProportions.width / 2) < r // Left Half
				&& t < y1 + (this.helperProportions.height / 2) // Bottom Half
				&& y2 - (this.helperProportions.height / 2) < b ); // Top Half

		}
	},

	_intersectsWithPointer: function(item) {

		var isOverElementHeight = $.ui.isOverAxis(this.positionAbs.top + this.offset.click.top, item.top, item.height),
			isOverElementWidth = $.ui.isOverAxis(this.positionAbs.left + this.offset.click.left, item.left, item.width),
			isOverElement = isOverElementHeight && isOverElementWidth,
			verticalDirection = this._getDragVerticalDirection(),
			horizontalDirection = this._getDragHorizontalDirection();

		if (!isOverElement)
			return false;

		return this.floating ?
			( ((horizontalDirection && horizontalDirection == "right") || verticalDirection == "down") ? 2 : 1 )
			: ( verticalDirection && (verticalDirection == "down" ? 2 : 1) );

	},

	_intersectsWithSides: function(item) {

		var isOverBottomHalf = $.ui.isOverAxis(this.positionAbs.top + this.offset.click.top, item.top + (item.height/2), item.height),
			isOverRightHalf = $.ui.isOverAxis(this.positionAbs.left + this.offset.click.left, item.left + (item.width/2), item.width),
			verticalDirection = this._getDragVerticalDirection(),
			horizontalDirection = this._getDragHorizontalDirection();

		if (this.floating && horizontalDirection) {
			return ((horizontalDirection == "right" && isOverRightHalf) || (horizontalDirection == "left" && !isOverRightHalf));
		} else {
			return verticalDirection && ((verticalDirection == "down" && isOverBottomHalf) || (verticalDirection == "up" && !isOverBottomHalf));
		}

	},

	_getDragVerticalDirection: function() {
		var delta = this.positionAbs.top - this.lastPositionAbs.top;
		return delta != 0 && (delta > 0 ? "down" : "up");
	},

	_getDragHorizontalDirection: function() {
		var delta = this.positionAbs.left - this.lastPositionAbs.left;
		return delta != 0 && (delta > 0 ? "right" : "left");
	},

	refresh: function(event) {
		this._refreshItems(event);
		this.refreshPositions();
		return this;
	},

	_connectWith: function() {
		var options = this.options;
		return options.connectWith.constructor == String
			? [options.connectWith]
			: options.connectWith;
	},
	
	_getItemsAsjQuery: function(connected) {

		var self = this;
		var items = [];
		var queries = [];
		var connectWith = this._connectWith();

		if(connectWith && connected) {
			for (var i = connectWith.length - 1; i >= 0; i--){
				var cur = $(connectWith[i]);
				for (var j = cur.length - 1; j >= 0; j--){
					var inst = $.data(cur[j], 'sortable');
					if(inst && inst != this && !inst.options.disabled) {
						queries.push([$.isFunction(inst.options.items) ? inst.options.items.call(inst.element) : $(inst.options.items, inst.element).not(".ui-sortable-helper").not('.ui-sortable-placeholder'), inst]);
					}
				};
			};
		}

		queries.push([$.isFunction(this.options.items) ? this.options.items.call(this.element, null, { options: this.options, item: this.currentItem }) : $(this.options.items, this.element).not(".ui-sortable-helper").not('.ui-sortable-placeholder'), this]);

		for (var i = queries.length - 1; i >= 0; i--){
			queries[i][0].each(function() {
				items.push(this);
			});
		};

		return $(items);

	},

	_removeCurrentsFromItems: function() {

		var list = this.currentItem.find(":data(sortable-item)");

		for (var i=0; i < this.items.length; i++) {

			for (var j=0; j < list.length; j++) {
				if(list[j] == this.items[i].item[0])
					this.items.splice(i,1);
			};

		};

	},

	_refreshItems: function(event) {

		this.items = [];
		this.containers = [this];
		var items = this.items;
		var self = this;
		var queries = [[$.isFunction(this.options.items) ? this.options.items.call(this.element[0], event, { item: this.currentItem }) : $(this.options.items, this.element), this]];
		var connectWith = this._connectWith();

		if(connectWith) {
			for (var i = connectWith.length - 1; i >= 0; i--){
				var cur = $(connectWith[i]);
				for (var j = cur.length - 1; j >= 0; j--){
					var inst = $.data(cur[j], 'sortable');
					if(inst && inst != this && !inst.options.disabled) {
						queries.push([$.isFunction(inst.options.items) ? inst.options.items.call(inst.element[0], event, { item: this.currentItem }) : $(inst.options.items, inst.element), inst]);
						this.containers.push(inst);
					}
				};
			};
		}

		for (var i = queries.length - 1; i >= 0; i--) {
			var targetData = queries[i][1];
			var _queries = queries[i][0];

			for (var j=0, queriesLength = _queries.length; j < queriesLength; j++) {
				var item = $(_queries[j]);

				item.data('sortable-item', targetData); // Data for target checking (mouse manager)

				items.push({
					item: item,
					instance: targetData,
					width: 0, height: 0,
					left: 0, top: 0
				});
			};
		};

	},

	refreshPositions: function(fast) {

		//This has to be redone because due to the item being moved out/into the offsetParent, the offsetParent's position will change
		if(this.offsetParent && this.helper) {
			this.offset.parent = this._getParentOffset();
		}

		for (var i = this.items.length - 1; i >= 0; i--){
			var item = this.items[i];

			var t = this.options.toleranceElement ? $(this.options.toleranceElement, item.item) : item.item;

			if (!fast) {
				item.width = t.outerWidth();
				item.height = t.outerHeight();
			}

			var p = t.offset();
			item.left = p.left;
			item.top = p.top;
		};

		if(this.options.custom && this.options.custom.refreshContainers) {
			this.options.custom.refreshContainers.call(this);
		} else {
			for (var i = this.containers.length - 1; i >= 0; i--){
				var p = this.containers[i].element.offset();
				this.containers[i].containerCache.left = p.left;
				this.containers[i].containerCache.top = p.top;
				this.containers[i].containerCache.width	= this.containers[i].element.outerWidth();
				this.containers[i].containerCache.height = this.containers[i].element.outerHeight();
			};
		}

		return this;
	},

	_createPlaceholder: function(that) {

		var self = that || this, o = self.options;

		if(!o.placeholder || o.placeholder.constructor == String) {
			var className = o.placeholder;
			o.placeholder = {
				element: function() {

					var el = $(document.createElement(self.currentItem[0].nodeName))
						.addClass(className || self.currentItem[0].className+" ui-sortable-placeholder")
						.removeClass("ui-sortable-helper")[0];

					if(!className)
						el.style.visibility = "hidden";

					return el;
				},
				update: function(container, p) {

					// 1. If a className is set as 'placeholder option, we don't force sizes - the class is responsible for that
					// 2. The option 'forcePlaceholderSize can be enabled to force it even if a class name is specified
					if(className && !o.forcePlaceholderSize) return;

					//If the element doesn't have a actual height by itself (without styles coming from a stylesheet), it receives the inline height from the dragged item
					if(!p.height()) { p.height(self.currentItem.innerHeight() - parseInt(self.currentItem.css('paddingTop')||0, 10) - parseInt(self.currentItem.css('paddingBottom')||0, 10)); };
					if(!p.width()) { p.width(self.currentItem.innerWidth() - parseInt(self.currentItem.css('paddingLeft')||0, 10) - parseInt(self.currentItem.css('paddingRight')||0, 10)); };
				}
			};
		}

		//Create the placeholder
		self.placeholder = $(o.placeholder.element.call(self.element, self.currentItem));

		//Append it after the actual current item
		self.currentItem.after(self.placeholder);

		//Update the size of the placeholder (TODO: Logic to fuzzy, see line 316/317)
		o.placeholder.update(self, self.placeholder);

	},

	_contactContainers: function(event) {
		
		// get innermost container that intersects with item 
		var innermostContainer = null, innermostIndex = null;		
		
		
		for (var i = this.containers.length - 1; i >= 0; i--){

			// never consider a container that's located within the item itself 
			if($.ui.contains(this.currentItem[0], this.containers[i].element[0]))
				continue;

			if(this._intersectsWith(this.containers[i].containerCache)) {

				// if we've already found a container and it's more "inner" than this, then continue 
				if(innermostContainer && $.ui.contains(this.containers[i].element[0], innermostContainer.element[0]))
					continue;

				innermostContainer = this.containers[i]; 
				innermostIndex = i;
					
			} else {
				// container doesn't intersect. trigger "out" event if necessary 
				if(this.containers[i].containerCache.over) {
					this.containers[i]._trigger("out", event, this._uiHash(this));
					this.containers[i].containerCache.over = 0;
				}
			}

		}
		
		// if no intersecting containers found, return 
		if(!innermostContainer) return; 

		// move the item into the container if it's not there already
		if(this.containers.length === 1) {
			this.containers[innermostIndex]._trigger("over", event, this._uiHash(this));
			this.containers[innermostIndex].containerCache.over = 1;
		} else if(this.currentContainer != this.containers[innermostIndex]) { 

			//When entering a new container, we will find the item with the least distance and append our item near it 
			var dist = 10000; var itemWithLeastDistance = null; var base = this.positionAbs[this.containers[innermostIndex].floating ? 'left' : 'top']; 
			for (var j = this.items.length - 1; j >= 0; j--) { 
				if(!$.ui.contains(this.containers[innermostIndex].element[0], this.items[j].item[0])) continue; 
				var cur = this.items[j][this.containers[innermostIndex].floating ? 'left' : 'top']; 
				if(Math.abs(cur - base) < dist) { 
					dist = Math.abs(cur - base); itemWithLeastDistance = this.items[j]; 
				} 
			} 

			if(!itemWithLeastDistance && !this.options.dropOnEmpty) //Check if dropOnEmpty is enabled 
				return; 

			this.currentContainer = this.containers[innermostIndex]; 
			itemWithLeastDistance ? this._rearrange(event, itemWithLeastDistance, null, true) : this._rearrange(event, null, this.containers[innermostIndex].element, true); 
			this._trigger("change", event, this._uiHash()); 
			this.containers[innermostIndex]._trigger("change", event, this._uiHash(this)); 

			//Update the placeholder 
			this.options.placeholder.update(this.currentContainer, this.placeholder); 
		
			this.containers[innermostIndex]._trigger("over", event, this._uiHash(this)); 
			this.containers[innermostIndex].containerCache.over = 1;
		} 
	
		
	},

	_createHelper: function(event) {

		var o = this.options;
		var helper = $.isFunction(o.helper) ? $(o.helper.apply(this.element[0], [event, this.currentItem])) : (o.helper == 'clone' ? this.currentItem.clone() : this.currentItem);

		if(!helper.parents('body').length) //Add the helper to the DOM if that didn't happen already
			$(o.appendTo != 'parent' ? o.appendTo : this.currentItem[0].parentNode)[0].appendChild(helper[0]);

		if(helper[0] == this.currentItem[0])
			this._storedCSS = { width: this.currentItem[0].style.width, height: this.currentItem[0].style.height, position: this.currentItem.css("position"), top: this.currentItem.css("top"), left: this.currentItem.css("left") };

		if(helper[0].style.width == '' || o.forceHelperSize) helper.width(this.currentItem.width());
		if(helper[0].style.height == '' || o.forceHelperSize) helper.height(this.currentItem.height());

		return helper;

	},

	_adjustOffsetFromHelper: function(obj) {
		if (typeof obj == 'string') {
			obj = obj.split(' ');
		}
		if ($.isArray(obj)) {
			obj = {left: +obj[0], top: +obj[1] || 0};
		}
		if ('left' in obj) {
			this.offset.click.left = obj.left + this.margins.left;
		}
		if ('right' in obj) {
			this.offset.click.left = this.helperProportions.width - obj.right + this.margins.left;
		}
		if ('top' in obj) {
			this.offset.click.top = obj.top + this.margins.top;
		}
		if ('bottom' in obj) {
			this.offset.click.top = this.helperProportions.height - obj.bottom + this.margins.top;
		}
	},

	_getParentOffset: function() {


		//Get the offsetParent and cache its position
		this.offsetParent = this.helper.offsetParent();
		var po = this.offsetParent.offset();

		// This is a special case where we need to modify a offset calculated on start, since the following happened:
		// 1. The position of the helper is absolute, so it's position is calculated based on the next positioned parent
		// 2. The actual offset parent is a child of the scroll parent, and the scroll parent isn't the document, which means that
		//    the scroll is included in the initial calculation of the offset of the parent, and never recalculated upon drag
		if(this.cssPosition == 'absolute' && this.scrollParent[0] != document && $.ui.contains(this.scrollParent[0], this.offsetParent[0])) {
			po.left += this.scrollParent.scrollLeft();
			po.top += this.scrollParent.scrollTop();
		}

		if((this.offsetParent[0] == document.body) //This needs to be actually done for all browsers, since pageX/pageY includes this information
		|| (this.offsetParent[0].tagName && this.offsetParent[0].tagName.toLowerCase() == 'html' && $.browser.msie)) //Ugly IE fix
			po = { top: 0, left: 0 };

		return {
			top: po.top + (parseInt(this.offsetParent.css("borderTopWidth"),10) || 0),
			left: po.left + (parseInt(this.offsetParent.css("borderLeftWidth"),10) || 0)
		};

	},

	_getRelativeOffset: function() {

		if(this.cssPosition == "relative") {
			var p = this.currentItem.position();
			return {
				top: p.top - (parseInt(this.helper.css("top"),10) || 0) + this.scrollParent.scrollTop(),
				left: p.left - (parseInt(this.helper.css("left"),10) || 0) + this.scrollParent.scrollLeft()
			};
		} else {
			return { top: 0, left: 0 };
		}

	},

	_cacheMargins: function() {
		this.margins = {
			left: (parseInt(this.currentItem.css("marginLeft"),10) || 0),
			top: (parseInt(this.currentItem.css("marginTop"),10) || 0)
		};
	},

	_cacheHelperProportions: function() {
		this.helperProportions = {
			width: this.helper.outerWidth(),
			height: this.helper.outerHeight()
		};
	},

	_setContainment: function() {

		var o = this.options;
		if(o.containment == 'parent') o.containment = this.helper[0].parentNode;
		if(o.containment == 'document' || o.containment == 'window') this.containment = [
			0 - this.offset.relative.left - this.offset.parent.left,
			0 - this.offset.relative.top - this.offset.parent.top,
			$(o.containment == 'document' ? document : window).width() - this.helperProportions.width - this.margins.left,
			($(o.containment == 'document' ? document : window).height() || document.body.parentNode.scrollHeight) - this.helperProportions.height - this.margins.top
		];

		if(!(/^(document|window|parent)$/).test(o.containment)) {
			var ce = $(o.containment)[0];
			var co = $(o.containment).offset();
			var over = ($(ce).css("overflow") != 'hidden');

			this.containment = [
				co.left + (parseInt($(ce).css("borderLeftWidth"),10) || 0) + (parseInt($(ce).css("paddingLeft"),10) || 0) - this.margins.left,
				co.top + (parseInt($(ce).css("borderTopWidth"),10) || 0) + (parseInt($(ce).css("paddingTop"),10) || 0) - this.margins.top,
				co.left+(over ? Math.max(ce.scrollWidth,ce.offsetWidth) : ce.offsetWidth) - (parseInt($(ce).css("borderLeftWidth"),10) || 0) - (parseInt($(ce).css("paddingRight"),10) || 0) - this.helperProportions.width - this.margins.left,
				co.top+(over ? Math.max(ce.scrollHeight,ce.offsetHeight) : ce.offsetHeight) - (parseInt($(ce).css("borderTopWidth"),10) || 0) - (parseInt($(ce).css("paddingBottom"),10) || 0) - this.helperProportions.height - this.margins.top
			];
		}

	},

	_convertPositionTo: function(d, pos) {

		if(!pos) pos = this.position;
		var mod = d == "absolute" ? 1 : -1;
		var o = this.options, scroll = this.cssPosition == 'absolute' && !(this.scrollParent[0] != document && $.ui.contains(this.scrollParent[0], this.offsetParent[0])) ? this.offsetParent : this.scrollParent, scrollIsRootNode = (/(html|body)/i).test(scroll[0].tagName);

		return {
			top: (
				pos.top																	// The absolute mouse position
				+ this.offset.relative.top * mod										// Only for relative positioned nodes: Relative offset from element to offset parent
				+ this.offset.parent.top * mod											// The offsetParent's offset without borders (offset + border)
				- ($.browser.safari && this.cssPosition == 'fixed' ? 0 : ( this.cssPosition == 'fixed' ? -this.scrollParent.scrollTop() : ( scrollIsRootNode ? 0 : scroll.scrollTop() ) ) * mod)
			),
			left: (
				pos.left																// The absolute mouse position
				+ this.offset.relative.left * mod										// Only for relative positioned nodes: Relative offset from element to offset parent
				+ this.offset.parent.left * mod											// The offsetParent's offset without borders (offset + border)
				- ($.browser.safari && this.cssPosition == 'fixed' ? 0 : ( this.cssPosition == 'fixed' ? -this.scrollParent.scrollLeft() : scrollIsRootNode ? 0 : scroll.scrollLeft() ) * mod)
			)
		};

	},

	_generatePosition: function(event) {

		var o = this.options, scroll = this.cssPosition == 'absolute' && !(this.scrollParent[0] != document && $.ui.contains(this.scrollParent[0], this.offsetParent[0])) ? this.offsetParent : this.scrollParent, scrollIsRootNode = (/(html|body)/i).test(scroll[0].tagName);

		// This is another very weird special case that only happens for relative elements:
		// 1. If the css position is relative
		// 2. and the scroll parent is the document or similar to the offset parent
		// we have to refresh the relative offset during the scroll so there are no jumps
		if(this.cssPosition == 'relative' && !(this.scrollParent[0] != document && this.scrollParent[0] != this.offsetParent[0])) {
			this.offset.relative = this._getRelativeOffset();
		}

		var pageX = event.pageX;
		var pageY = event.pageY;

		/*
		 * - Position constraining -
		 * Constrain the position to a mix of grid, containment.
		 */

		if(this.originalPosition) { //If we are not dragging yet, we won't check for options

			if(this.containment) {
				if(event.pageX - this.offset.click.left < this.containment[0]) pageX = this.containment[0] + this.offset.click.left;
				if(event.pageY - this.offset.click.top < this.containment[1]) pageY = this.containment[1] + this.offset.click.top;
				if(event.pageX - this.offset.click.left > this.containment[2]) pageX = this.containment[2] + this.offset.click.left;
				if(event.pageY - this.offset.click.top > this.containment[3]) pageY = this.containment[3] + this.offset.click.top;
			}

			if(o.grid) {
				var top = this.originalPageY + Math.round((pageY - this.originalPageY) / o.grid[1]) * o.grid[1];
				pageY = this.containment ? (!(top - this.offset.click.top < this.containment[1] || top - this.offset.click.top > this.containment[3]) ? top : (!(top - this.offset.click.top < this.containment[1]) ? top - o.grid[1] : top + o.grid[1])) : top;

				var left = this.originalPageX + Math.round((pageX - this.originalPageX) / o.grid[0]) * o.grid[0];
				pageX = this.containment ? (!(left - this.offset.click.left < this.containment[0] || left - this.offset.click.left > this.containment[2]) ? left : (!(left - this.offset.click.left < this.containment[0]) ? left - o.grid[0] : left + o.grid[0])) : left;
			}

		}

		return {
			top: (
				pageY																// The absolute mouse position
				- this.offset.click.top													// Click offset (relative to the element)
				- this.offset.relative.top												// Only for relative positioned nodes: Relative offset from element to offset parent
				- this.offset.parent.top												// The offsetParent's offset without borders (offset + border)
				+ ($.browser.safari && this.cssPosition == 'fixed' ? 0 : ( this.cssPosition == 'fixed' ? -this.scrollParent.scrollTop() : ( scrollIsRootNode ? 0 : scroll.scrollTop() ) ))
			),
			left: (
				pageX																// The absolute mouse position
				- this.offset.click.left												// Click offset (relative to the element)
				- this.offset.relative.left												// Only for relative positioned nodes: Relative offset from element to offset parent
				- this.offset.parent.left												// The offsetParent's offset without borders (offset + border)
				+ ($.browser.safari && this.cssPosition == 'fixed' ? 0 : ( this.cssPosition == 'fixed' ? -this.scrollParent.scrollLeft() : scrollIsRootNode ? 0 : scroll.scrollLeft() ))
			)
		};

	},

	_rearrange: function(event, i, a, hardRefresh) {

		a ? a[0].appendChild(this.placeholder[0]) : i.item[0].parentNode.insertBefore(this.placeholder[0], (this.direction == 'down' ? i.item[0] : i.item[0].nextSibling));

		//Various things done here to improve the performance:
		// 1. we create a setTimeout, that calls refreshPositions
		// 2. on the instance, we have a counter variable, that get's higher after every append
		// 3. on the local scope, we copy the counter variable, and check in the timeout, if it's still the same
		// 4. this lets only the last addition to the timeout stack through
		this.counter = this.counter ? ++this.counter : 1;
		var self = this, counter = this.counter;

		window.setTimeout(function() {
			if(counter == self.counter) self.refreshPositions(!hardRefresh); //Precompute after each DOM insertion, NOT on mousemove
		},0);

	},

	_clear: function(event, noPropagation) {

		this.reverting = false;
		// We delay all events that have to be triggered to after the point where the placeholder has been removed and
		// everything else normalized again
		var delayedTriggers = [], self = this;

		// We first have to update the dom position of the actual currentItem
		// Note: don't do it if the current item is already removed (by a user), or it gets reappended (see #4088)
		if(!this._noFinalSort && this.currentItem[0].parentNode) this.placeholder.before(this.currentItem);
		this._noFinalSort = null;

		if(this.helper[0] == this.currentItem[0]) {
			for(var i in this._storedCSS) {
				if(this._storedCSS[i] == 'auto' || this._storedCSS[i] == 'static') this._storedCSS[i] = '';
			}
			this.currentItem.css(this._storedCSS).removeClass("ui-sortable-helper");
		} else {
			this.currentItem.show();
		}

		if(this.fromOutside && !noPropagation) delayedTriggers.push(function(event) { this._trigger("receive", event, this._uiHash(this.fromOutside)); });
		if((this.fromOutside || this.domPosition.prev != this.currentItem.prev().not(".ui-sortable-helper")[0] || this.domPosition.parent != this.currentItem.parent()[0]) && !noPropagation) delayedTriggers.push(function(event) { this._trigger("update", event, this._uiHash()); }); //Trigger update callback if the DOM position has changed
		if(!$.ui.contains(this.element[0], this.currentItem[0])) { //Node was moved out of the current element
			if(!noPropagation) delayedTriggers.push(function(event) { this._trigger("remove", event, this._uiHash()); });
			for (var i = this.containers.length - 1; i >= 0; i--){
				if($.ui.contains(this.containers[i].element[0], this.currentItem[0]) && !noPropagation) {
					delayedTriggers.push((function(c) { return function(event) { c._trigger("receive", event, this._uiHash(this)); };  }).call(this, this.containers[i]));
					delayedTriggers.push((function(c) { return function(event) { c._trigger("update", event, this._uiHash(this));  }; }).call(this, this.containers[i]));
				}
			};
		};

		//Post events to containers
		for (var i = this.containers.length - 1; i >= 0; i--){
			if(!noPropagation) delayedTriggers.push((function(c) { return function(event) { c._trigger("deactivate", event, this._uiHash(this)); };  }).call(this, this.containers[i]));
			if(this.containers[i].containerCache.over) {
				delayedTriggers.push((function(c) { return function(event) { c._trigger("out", event, this._uiHash(this)); };  }).call(this, this.containers[i]));
				this.containers[i].containerCache.over = 0;
			}
		}

		//Do what was originally in plugins
		if(this._storedCursor) $('body').css("cursor", this._storedCursor); //Reset cursor
		if(this._storedOpacity) this.helper.css("opacity", this._storedOpacity); //Reset opacity
		if(this._storedZIndex) this.helper.css("zIndex", this._storedZIndex == 'auto' ? '' : this._storedZIndex); //Reset z-index

		this.dragging = false;
		if(this.cancelHelperRemoval) {
			if(!noPropagation) {
				this._trigger("beforeStop", event, this._uiHash());
				for (var i=0; i < delayedTriggers.length; i++) { delayedTriggers[i].call(this, event); }; //Trigger all delayed events
				this._trigger("stop", event, this._uiHash());
			}
			return false;
		}

		if(!noPropagation) this._trigger("beforeStop", event, this._uiHash());

		//$(this.placeholder[0]).remove(); would have been the jQuery way - unfortunately, it unbinds ALL events from the original node!
		this.placeholder[0].parentNode.removeChild(this.placeholder[0]);

		if(this.helper[0] != this.currentItem[0]) this.helper.remove(); this.helper = null;

		if(!noPropagation) {
			for (var i=0; i < delayedTriggers.length; i++) { delayedTriggers[i].call(this, event); }; //Trigger all delayed events
			this._trigger("stop", event, this._uiHash());
		}

		this.fromOutside = false;
		return true;

	},

	_trigger: function() {
		if ($.Widget.prototype._trigger.apply(this, arguments) === false) {
			this.cancel();
		}
	},

	_uiHash: function(inst) {
		var self = inst || this;
		return {
			helper: self.helper,
			placeholder: self.placeholder || $([]),
			position: self.position,
			originalPosition: self.originalPosition,
			offset: self.positionAbs,
			item: self.currentItem,
			sender: inst ? inst.element : null
		};
	}

});

$.extend($.ui.sortable, {
	version: "1.8.5"
});

})(jQuery);
/*
 * jQuery UI Slider 1.8.5
 *
 * Copyright 2010, AUTHORS.txt (http://jqueryui.com/about)
 * Dual licensed under the MIT or GPL Version 2 licenses.
 * http://jquery.org/license
 *
 * http://docs.jquery.com/UI/Slider
 *
 * Depends:
 *	jquery.ui.core.js
 *	jquery.ui.mouse.js
 *	jquery.ui.widget.js
 */
(function( $, undefined ) {

// number of pages in a slider
// (how many times can you page up/down to go through the whole range)
var numPages = 5;

$.widget( "ui.slider", $.ui.mouse, {

	widgetEventPrefix: "slide",

	options: {
		animate: false,
		distance: 0,
		max: 100,
		min: 0,
		orientation: "horizontal",
		range: false,
		step: 1,
		value: 0,
		values: null
	},

	_create: function() {
		var self = this,
			o = this.options;

		this._keySliding = false;
		this._mouseSliding = false;
		this._animateOff = true;
		this._handleIndex = null;
		this._detectOrientation();
		this._mouseInit();

		this.element
			.addClass( "ui-slider" +
				" ui-slider-" + this.orientation +
				" ui-widget" +
				" ui-widget-content" +
				" ui-corner-all" );
		
		if ( o.disabled ) {
			this.element.addClass( "ui-slider-disabled ui-disabled" );
		}

		this.range = $([]);

		if ( o.range ) {
			if ( o.range === true ) {
				this.range = $( "<div></div>" );
				if ( !o.values ) {
					o.values = [ this._valueMin(), this._valueMin() ];
				}
				if ( o.values.length && o.values.length !== 2 ) {
					o.values = [ o.values[0], o.values[0] ];
				}
			} else {
				this.range = $( "<div></div>" );
			}

			this.range
				.appendTo( this.element )
				.addClass( "ui-slider-range" );

			if ( o.range === "min" || o.range === "max" ) {
				this.range.addClass( "ui-slider-range-" + o.range );
			}

			// note: this isn't the most fittingly semantic framework class for this element,
			// but worked best visually with a variety of themes
			this.range.addClass( "ui-widget-header" );
		}

		if ( $( ".ui-slider-handle", this.element ).length === 0 ) {
			$( "<a href='#'></a>" )
				.appendTo( this.element )
				.addClass( "ui-slider-handle" );
		}

		if ( o.values && o.values.length ) {
			while ( $(".ui-slider-handle", this.element).length < o.values.length ) {
				$( "<a href='#'></a>" )
					.appendTo( this.element )
					.addClass( "ui-slider-handle" );
			}
		}

		this.handles = $( ".ui-slider-handle", this.element )
			.addClass( "ui-state-default" +
				" ui-corner-all" );

		this.handle = this.handles.eq( 0 );

		this.handles.add( this.range ).filter( "a" )
			.click(function( event ) {
				event.preventDefault();
			})
			.hover(function() {
				if ( !o.disabled ) {
					$( this ).addClass( "ui-state-hover" );
				}
			}, function() {
				$( this ).removeClass( "ui-state-hover" );
			})
			.focus(function() {
				if ( !o.disabled ) {
					$( ".ui-slider .ui-state-focus" ).removeClass( "ui-state-focus" );
					$( this ).addClass( "ui-state-focus" );
				} else {
					$( this ).blur();
				}
			})
			.blur(function() {
				$( this ).removeClass( "ui-state-focus" );
			});

		this.handles.each(function( i ) {
			$( this ).data( "index.ui-slider-handle", i );
		});

		this.handles
			.keydown(function( event ) {
				var ret = true,
					index = $( this ).data( "index.ui-slider-handle" ),
					allowed,
					curVal,
					newVal,
					step;
	
				if ( self.options.disabled ) {
					return;
				}
	
				switch ( event.keyCode ) {
					case $.ui.keyCode.HOME:
					case $.ui.keyCode.END:
					case $.ui.keyCode.PAGE_UP:
					case $.ui.keyCode.PAGE_DOWN:
					case $.ui.keyCode.UP:
					case $.ui.keyCode.RIGHT:
					case $.ui.keyCode.DOWN:
					case $.ui.keyCode.LEFT:
						ret = false;
						if ( !self._keySliding ) {
							self._keySliding = true;
							$( this ).addClass( "ui-state-active" );
							allowed = self._start( event, index );
							if ( allowed === false ) {
								return;
							}
						}
						break;
				}
	
				step = self.options.step;
				if ( self.options.values && self.options.values.length ) {
					curVal = newVal = self.values( index );
				} else {
					curVal = newVal = self.value();
				}
	
				switch ( event.keyCode ) {
					case $.ui.keyCode.HOME:
						newVal = self._valueMin();
						break;
					case $.ui.keyCode.END:
						newVal = self._valueMax();
						break;
					case $.ui.keyCode.PAGE_UP:
						newVal = self._trimAlignValue( curVal + ( (self._valueMax() - self._valueMin()) / numPages ) );
						break;
					case $.ui.keyCode.PAGE_DOWN:
						newVal = self._trimAlignValue( curVal - ( (self._valueMax() - self._valueMin()) / numPages ) );
						break;
					case $.ui.keyCode.UP:
					case $.ui.keyCode.RIGHT:
						if ( curVal === self._valueMax() ) {
							return;
						}
						newVal = self._trimAlignValue( curVal + step );
						break;
					case $.ui.keyCode.DOWN:
					case $.ui.keyCode.LEFT:
						if ( curVal === self._valueMin() ) {
							return;
						}
						newVal = self._trimAlignValue( curVal - step );
						break;
				}
	
				self._slide( event, index, newVal );
	
				return ret;
	
			})
			.keyup(function( event ) {
				var index = $( this ).data( "index.ui-slider-handle" );
	
				if ( self._keySliding ) {
					self._keySliding = false;
					self._stop( event, index );
					self._change( event, index );
					$( this ).removeClass( "ui-state-active" );
				}
	
			});

		this._refreshValue();

		this._animateOff = false;
	},

	destroy: function() {
		this.handles.remove();
		this.range.remove();

		this.element
			.removeClass( "ui-slider" +
				" ui-slider-horizontal" +
				" ui-slider-vertical" +
				" ui-slider-disabled" +
				" ui-widget" +
				" ui-widget-content" +
				" ui-corner-all" )
			.removeData( "slider" )
			.unbind( ".slider" );

		this._mouseDestroy();

		return this;
	},

	_mouseCapture: function( event ) {
		var o = this.options,
			position,
			normValue,
			distance,
			closestHandle,
			self,
			index,
			allowed,
			offset,
			mouseOverHandle;

		if ( o.disabled ) {
			return false;
		}

		this.elementSize = {
			width: this.element.outerWidth(),
			height: this.element.outerHeight()
		};
		this.elementOffset = this.element.offset();

		position = { x: event.pageX, y: event.pageY };
		normValue = this._normValueFromMouse( position );
		distance = this._valueMax() - this._valueMin() + 1;
		self = this;
		this.handles.each(function( i ) {
			var thisDistance = Math.abs( normValue - self.values(i) );
			if ( distance > thisDistance ) {
				distance = thisDistance;
				closestHandle = $( this );
				index = i;
			}
		});

		// workaround for bug #3736 (if both handles of a range are at 0,
		// the first is always used as the one with least distance,
		// and moving it is obviously prevented by preventing negative ranges)
		if( o.range === true && this.values(1) === o.min ) {
			index += 1;
			closestHandle = $( this.handles[index] );
		}

		allowed = this._start( event, index );
		if ( allowed === false ) {
			return false;
		}
		this._mouseSliding = true;

		self._handleIndex = index;

		closestHandle
			.addClass( "ui-state-active" )
			.focus();
		
		offset = closestHandle.offset();
		mouseOverHandle = !$( event.target ).parents().andSelf().is( ".ui-slider-handle" );
		this._clickOffset = mouseOverHandle ? { left: 0, top: 0 } : {
			left: event.pageX - offset.left - ( closestHandle.width() / 2 ),
			top: event.pageY - offset.top -
				( closestHandle.height() / 2 ) -
				( parseInt( closestHandle.css("borderTopWidth"), 10 ) || 0 ) -
				( parseInt( closestHandle.css("borderBottomWidth"), 10 ) || 0) +
				( parseInt( closestHandle.css("marginTop"), 10 ) || 0)
		};

		this._slide( event, index, normValue );
		this._animateOff = true;
		return true;
	},

	_mouseStart: function( event ) {
		return true;
	},

	_mouseDrag: function( event ) {
		var position = { x: event.pageX, y: event.pageY },
			normValue = this._normValueFromMouse( position );
		
		this._slide( event, this._handleIndex, normValue );

		return false;
	},

	_mouseStop: function( event ) {
		this.handles.removeClass( "ui-state-active" );
		this._mouseSliding = false;

		this._stop( event, this._handleIndex );
		this._change( event, this._handleIndex );

		this._handleIndex = null;
		this._clickOffset = null;
		this._animateOff = false;

		return false;
	},
	
	_detectOrientation: function() {
		this.orientation = ( this.options.orientation === "vertical" ) ? "vertical" : "horizontal";
	},

	_normValueFromMouse: function( position ) {
		var pixelTotal,
			pixelMouse,
			percentMouse,
			valueTotal,
			valueMouse;

		if ( this.orientation === "horizontal" ) {
			pixelTotal = this.elementSize.width;
			pixelMouse = position.x - this.elementOffset.left - ( this._clickOffset ? this._clickOffset.left : 0 );
		} else {
			pixelTotal = this.elementSize.height;
			pixelMouse = position.y - this.elementOffset.top - ( this._clickOffset ? this._clickOffset.top : 0 );
		}

		percentMouse = ( pixelMouse / pixelTotal );
		if ( percentMouse > 1 ) {
			percentMouse = 1;
		}
		if ( percentMouse < 0 ) {
			percentMouse = 0;
		}
		if ( this.orientation === "vertical" ) {
			percentMouse = 1 - percentMouse;
		}

		valueTotal = this._valueMax() - this._valueMin();
		valueMouse = this._valueMin() + percentMouse * valueTotal;

		return this._trimAlignValue( valueMouse );
	},

	_start: function( event, index ) {
		var uiHash = {
			handle: this.handles[ index ],
			value: this.value()
		};
		if ( this.options.values && this.options.values.length ) {
			uiHash.value = this.values( index );
			uiHash.values = this.values();
		}
		return this._trigger( "start", event, uiHash );
	},

	_slide: function( event, index, newVal ) {
		var otherVal,
			newValues,
			allowed;

		if ( this.options.values && this.options.values.length ) {
			otherVal = this.values( index ? 0 : 1 );

			if ( ( this.options.values.length === 2 && this.options.range === true ) && 
					( ( index === 0 && newVal > otherVal) || ( index === 1 && newVal < otherVal ) )
				) {
				newVal = otherVal;
			}

			if ( newVal !== this.values( index ) ) {
				newValues = this.values();
				newValues[ index ] = newVal;
				// A slide can be canceled by returning false from the slide callback
				allowed = this._trigger( "slide", event, {
					handle: this.handles[ index ],
					value: newVal,
					values: newValues
				} );
				otherVal = this.values( index ? 0 : 1 );
				if ( allowed !== false ) {
					this.values( index, newVal, true );
				}
			}
		} else {
			if ( newVal !== this.value() ) {
				// A slide can be canceled by returning false from the slide callback
				allowed = this._trigger( "slide", event, {
					handle: this.handles[ index ],
					value: newVal
				} );
				if ( allowed !== false ) {
					this.value( newVal );
				}
			}
		}
	},

	_stop: function( event, index ) {
		var uiHash = {
			handle: this.handles[ index ],
			value: this.value()
		};
		if ( this.options.values && this.options.values.length ) {
			uiHash.value = this.values( index );
			uiHash.values = this.values();
		}

		this._trigger( "stop", event, uiHash );
	},

	_change: function( event, index ) {
		if ( !this._keySliding && !this._mouseSliding ) {
			var uiHash = {
				handle: this.handles[ index ],
				value: this.value()
			};
			if ( this.options.values && this.options.values.length ) {
				uiHash.value = this.values( index );
				uiHash.values = this.values();
			}

			this._trigger( "change", event, uiHash );
		}
	},

	value: function( newValue ) {
		if ( arguments.length ) {
			this.options.value = this._trimAlignValue( newValue );
			this._refreshValue();
			this._change( null, 0 );
		}

		return this._value();
	},

	values: function( index, newValue ) {
		var vals,
			newValues,
			i;

		if ( arguments.length > 1 ) {
			this.options.values[ index ] = this._trimAlignValue( newValue );
			this._refreshValue();
			this._change( null, index );
		}

		if ( arguments.length ) {
			if ( $.isArray( arguments[ 0 ] ) ) {
				vals = this.options.values;
				newValues = arguments[ 0 ];
				for ( i = 0; i < vals.length; i += 1 ) {
					vals[ i ] = this._trimAlignValue( newValues[ i ] );
					this._change( null, i );
				}
				this._refreshValue();
			} else {
				if ( this.options.values && this.options.values.length ) {
					return this._values( index );
				} else {
					return this.value();
				}
			}
		} else {
			return this._values();
		}
	},

	_setOption: function( key, value ) {
		var i,
			valsLength = 0;

		if ( $.isArray( this.options.values ) ) {
			valsLength = this.options.values.length;
		}

		$.Widget.prototype._setOption.apply( this, arguments );

		switch ( key ) {
			case "disabled":
				if ( value ) {
					this.handles.filter( ".ui-state-focus" ).blur();
					this.handles.removeClass( "ui-state-hover" );
					this.handles.attr( "disabled", "disabled" );
					this.element.addClass( "ui-disabled" );
				} else {
					this.handles.removeAttr( "disabled" );
					this.element.removeClass( "ui-disabled" );
				}
				break;
			case "orientation":
				this._detectOrientation();
				this.element
					.removeClass( "ui-slider-horizontal ui-slider-vertical" )
					.addClass( "ui-slider-" + this.orientation );
				this._refreshValue();
				break;
			case "value":
				this._animateOff = true;
				this._refreshValue();
				this._change( null, 0 );
				this._animateOff = false;
				break;
			case "values":
				this._animateOff = true;
				this._refreshValue();
				for ( i = 0; i < valsLength; i += 1 ) {
					this._change( null, i );
				}
				this._animateOff = false;
				break;
		}
	},

	//internal value getter
	// _value() returns value trimmed by min and max, aligned by step
	_value: function() {
		var val = this.options.value;
		val = this._trimAlignValue( val );

		return val;
	},

	//internal values getter
	// _values() returns array of values trimmed by min and max, aligned by step
	// _values( index ) returns single value trimmed by min and max, aligned by step
	_values: function( index ) {
		var val,
			vals,
			i;

		if ( arguments.length ) {
			val = this.options.values[ index ];
			val = this._trimAlignValue( val );

			return val;
		} else {
			// .slice() creates a copy of the array
			// this copy gets trimmed by min and max and then returned
			vals = this.options.values.slice();
			for ( i = 0; i < vals.length; i+= 1) {
				vals[ i ] = this._trimAlignValue( vals[ i ] );
			}

			return vals;
		}
	},
	
	// returns the step-aligned value that val is closest to, between (inclusive) min and max
	_trimAlignValue: function( val ) {
		if ( val < this._valueMin() ) {
			return this._valueMin();
		}
		if ( val > this._valueMax() ) {
			return this._valueMax();
		}
		var step = ( this.options.step > 0 ) ? this.options.step : 1,
			valModStep = val % step,
			alignValue = val - valModStep;

		if ( Math.abs(valModStep) * 2 >= step ) {
			alignValue += ( valModStep > 0 ) ? step : ( -step );
		}

		// Since JavaScript has problems with large floats, round
		// the final value to 5 digits after the decimal point (see #4124)
		return parseFloat( alignValue.toFixed(5) );
	},

	_valueMin: function() {
		return this.options.min;
	},

	_valueMax: function() {
		return this.options.max;
	},
	
	_refreshValue: function() {
		var oRange = this.options.range,
			o = this.options,
			self = this,
			animate = ( !this._animateOff ) ? o.animate : false,
			valPercent,
			_set = {},
			lastValPercent,
			value,
			valueMin,
			valueMax;

		if ( this.options.values && this.options.values.length ) {
			this.handles.each(function( i, j ) {
				valPercent = ( self.values(i) - self._valueMin() ) / ( self._valueMax() - self._valueMin() ) * 100;
				_set[ self.orientation === "horizontal" ? "left" : "bottom" ] = valPercent + "%";
				$( this ).stop( 1, 1 )[ animate ? "animate" : "css" ]( _set, o.animate );
				if ( self.options.range === true ) {
					if ( self.orientation === "horizontal" ) {
						if ( i === 0 ) {
							self.range.stop( 1, 1 )[ animate ? "animate" : "css" ]( { left: valPercent + "%" }, o.animate );
						}
						if ( i === 1 ) {
							self.range[ animate ? "animate" : "css" ]( { width: ( valPercent - lastValPercent ) + "%" }, { queue: false, duration: o.animate } );
						}
					} else {
						if ( i === 0 ) {
							self.range.stop( 1, 1 )[ animate ? "animate" : "css" ]( { bottom: ( valPercent ) + "%" }, o.animate );
						}
						if ( i === 1 ) {
							self.range[ animate ? "animate" : "css" ]( { height: ( valPercent - lastValPercent ) + "%" }, { queue: false, duration: o.animate } );
						}
					}
				}
				lastValPercent = valPercent;
			});
		} else {
			value = this.value();
			valueMin = this._valueMin();
			valueMax = this._valueMax();
			valPercent = ( valueMax !== valueMin ) ?
					( value - valueMin ) / ( valueMax - valueMin ) * 100 :
					0;
			_set[ self.orientation === "horizontal" ? "left" : "bottom" ] = valPercent + "%";
			this.handle.stop( 1, 1 )[ animate ? "animate" : "css" ]( _set, o.animate );

			if ( oRange === "min" && this.orientation === "horizontal" ) {
				this.range.stop( 1, 1 )[ animate ? "animate" : "css" ]( { width: valPercent + "%" }, o.animate );
			}
			if ( oRange === "max" && this.orientation === "horizontal" ) {
				this.range[ animate ? "animate" : "css" ]( { width: ( 100 - valPercent ) + "%" }, { queue: false, duration: o.animate } );
			}
			if ( oRange === "min" && this.orientation === "vertical" ) {
				this.range.stop( 1, 1 )[ animate ? "animate" : "css" ]( { height: valPercent + "%" }, o.animate );
			}
			if ( oRange === "max" && this.orientation === "vertical" ) {
				this.range[ animate ? "animate" : "css" ]( { height: ( 100 - valPercent ) + "%" }, { queue: false, duration: o.animate } );
			}
		}
	}

});

$.extend( $.ui.slider, {
	version: "1.8.5"
});

}(jQuery));
