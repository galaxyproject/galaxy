$.ui = {
	getPointer: function(e) {
		var x = e.pageX || (e.clientX + (document.documentElement.scrollLeft || document.body.scrollLeft)) || 0;
		var y = e.pageY || (e.clientY + (document.documentElement.scrollTop || document.body.scrollTop)) || 0;
		return [x,y];
	},
	plugin: function(what, calltime, option, plugin) {
		if(!$.ui[what].prototype.plugins[calltime]) $.ui[what].prototype.plugins[calltime] = [];
		$.ui[what].prototype.plugins[calltime].push([option,plugin]);
	},
	num: function(el, prop) {
		return parseInt($.css(el.jquery?el[0]:el,prop))||0;
	},
	//Generic methods for object oriented plugins
	manager: {},
	get: function(n, t) {
		return $.ui.manager[t] ? $.ui.manager[t][n] : null;	
	},
	add: function(n, t, w) {
		if(!$.ui.manager[t]) $.ui.manager[t] = {};

		if($.ui.manager[t][n])
			$.ui.manager[t][n].push(w);
		else
			$.ui.manager[t][n] = [w];
	}
};

(function($) {
	
	$.ui.mouseInteraction = function(el,o) {
	
		if(!o) var o = {};
		this.element = el;
		
		this.options = {};
		$.extend(this.options, o);
		$.extend(this.options, {
			handle : o.handle ? ($(o.handle, el)[0] ? $(o.handle, el) : $(el)) : $(el),
			helper: o.helper ? o.helper : 'original',
			preventionDistance: o.preventionDistance ? o.preventionDistance : 0,
			dragPrevention: o.dragPrevention ? o.dragPrevention.toLowerCase().split(',') : ['input','textarea','button','select','option'],
			cursorAt: { top: ((o.cursorAt && o.cursorAt.top) ? o.cursorAt.top : 0), left: ((o.cursorAt && o.cursorAt.left) ? o.cursorAt.left : 0), bottom: ((o.cursorAt && o.cursorAt.bottom) ? o.cursorAt.bottom : 0), right: ((o.cursorAt && o.cursorAt.right) ? o.cursorAt.right : 0) },
			cursorAtIgnore: (!o.cursorAt) ? true : false, //Internal property
			appendTo: o.appendTo ? o.appendTo : 'parent'			
		});
		o = this.options; //Just Lazyness
		
		if(!this.options.nonDestructive && (o.helper == 'clone' || o.helper == 'original')) {

			// Let's save the margins for better reference
			o.margins = {
				top: $.ui.num(el,'marginTop'),
				left: $.ui.num(el,'marginLeft'),
				bottom: $.ui.num(el,'marginBottom'),
				right: $.ui.num(el,'marginRight')
			};

			// We have to add margins to our cursorAt
			if(o.cursorAt.top != 0) o.cursorAt.top += o.margins.top;
			if(o.cursorAt.left != 0) o.cursorAt.left += o.margins.left;
			if(o.cursorAt.bottom != 0) o.cursorAt.bottom += o.margins.bottom;
			if(o.cursorAt.right != 0) o.cursorAt.right += o.margins.right;
			
			if(o.helper == 'original')
				o.wasPositioned = $(el).css('position');
			
		} else {
			o.margins = { top: 0, left: 0, right: 0, bottom: 0 };
		}
		
		var self = this;
		this.mousedownfunc = function(e) { // Bind the mousedown event
			return self.click.apply(self, [e]);	
		};
		o.handle.bind('mousedown', this.mousedownfunc);
		
		//Prevent selection of text when starting the drag in IE
		if($.browser.msie) $(this.element).attr('unselectable', 'on');
		
	};
	
	$.extend($.ui.mouseInteraction.prototype, {
		plugins: {},
		pos: null,
		opos: null,
		currentTarget: null,
		lastTarget: null,
		helper: null,
		timer: null,
		slowMode: false,
		element: null,
		init: false,
		destroy: function() {
			this.options.handle.unbind('mousedown', this.mousedownfunc);
		},
		click: function(e) {

			window.focus();
			if(e.which != 1) return true; //only left click starts dragging
		
			// Prevent execution on defined elements
			var targetName = (e.target) ? e.target.nodeName.toLowerCase() : e.srcElement.nodeName.toLowerCase();
			for(var i=0;i<this.options.dragPrevention.length;i++) {
				if(targetName == this.options.dragPrevention[i]) return true;
			}
			
			//Prevent execution on condition
			if(this.options.startCondition && !this.options.startCondition.apply(this, [e])) {
				return true;
			}

			var self = this;
			this.mouseup = function(e) {
					return self.stop.apply(self, [e]);
			};
			this.mousemove = function(e) {
					return self.drag.apply(self, [e]);
			};
			
			var initFunc = function() { //This function get's called at bottom or after timeout
	
				$(document).bind('mouseup', self.mouseup);
				$(document).bind('mousemove', self.mousemove);

				self.opos = $.ui.getPointer(e); // Get the original mouse position

			};
			
			if(this.options.preventionTimeout) { //use prevention timeout
				if(this.timer) clearInterval(this.timer);
				this.timer = setTimeout(function() { initFunc(); }, this.options.preventionTimeout);
				return false;
			}
		
			initFunc();
			return false;
			
		},
		start: function(e) {
			
			var o = this.options;
			o.curOffset = $(this.element).offset({ border: false }); //get the current offset
				
			if(typeof o.helper == 'function') { //If helper is a function, use the node returned by it
				this.helper = o.helper.apply(this.element, [e,this]);
			} else { //No custom helper
				if(o.helper == 'clone') this.helper = $(this.element).clone()[0];
				if(o.helper == 'original') this.helper = this.element;
			}
			
			if(o.appendTo == 'parent') { // Let's see if we have a positioned parent
				var curParent = this.element.parentNode;
				while (curParent) {
					if(curParent.style && ($(curParent).css('position') == 'relative' || $(curParent).css('position') == 'absolute')) {
						o.pp = curParent;
						o.po = $(curParent).offset({ border: false });
						o.ppOverflow = !!($(o.pp).css('overflow') == 'auto' || $(o.pp).css('overflow') == 'scroll'); //TODO!
						break;	
					}
					curParent = curParent.parentNode ? curParent.parentNode : null;
				};
				
				if(!o.pp) o.po = { top: 0, left: 0 };
			}
			
			this.pos = [this.opos[0],this.opos[1]]; //Use the actual clicked position
			
			if(o.cursorAtIgnore) { // If we want to pick the element where we clicked, we borrow cursorAt and add margins
				o.cursorAt.left = this.pos[0] - o.curOffset.left + o.margins.left;
				o.cursorAt.top = this.pos[1] - o.curOffset.top + o.margins.top;
			}

			//Save the real mouse position
			this.rpos = [this.pos[0],this.pos[1]];
			
			if(o.pp) { // If we have a positioned parent, we pick the draggable relative to it
				this.pos[0] -= o.po.left;
				this.pos[1] -= o.po.top;
			}
			
			this.slowMode = (o.cursorAt && (o.cursorAt.top-o.margins.top > 0 || o.cursorAt.bottom-o.margins.bottom > 0) && (o.cursorAt.left-o.margins.left > 0 || o.cursorAt.right-o.margins.right > 0)) ? true : false; //If cursorAt is within the helper, set slowMode to true
			
			if(!o.nonDestructive) $(this.helper).css('position', 'absolute');
			if(o.helper != 'original') $(this.helper).appendTo((o.appendTo == 'parent' ? this.element.parentNode : o.appendTo));


			// Remap right/bottom properties for cursorAt to left/top
			if(o.cursorAt.right && !o.cursorAt.left) o.cursorAt.left = this.helper.offsetWidth+o.margins.right+o.margins.left - o.cursorAt.right;
			if(o.cursorAt.bottom && !o.cursorAt.top) o.cursorAt.top = this.helper.offsetHeight+o.margins.top+o.margins.bottom - o.cursorAt.bottom;
		
			this.init = true;	

			if(o._start) o._start.apply(this.element, [this.helper, this.pos, o.cursorAt, this]); // Trigger the onStart callback
			return false;
						
		},
		stop: function(e) {			
			
			var o = this.options;
			
			var self = this;
			$(document).unbind('mouseup', self.mouseup);
			$(document).unbind('mousemove', self.mousemove);

			if(this.init == false) {
			    // james@bx.psu.edu
			    if ( o.click ) { o.click.apply(); }
				return this.opos = this.pos = null;
			}
			
			if(o._beforeStop) o._beforeStop.apply(this.element, [this.helper, this.pos, o.cursorAt, this]);

				
			if(this.helper != this.element && !o.beQuietAtEnd) { // Remove helper, if it's not the original node
				$(this.helper).remove();
				this.helper = null;
			}
			
			if(!o.beQuietAtEnd && o.wasPositioned)
				$(this.element).css('position', o.wasPositioned);
				
			if(!o.beQuietAtEnd && o._stop) o._stop.apply(this.element, [this.helper, this.pos, o.cursorAt, this]);

			this.init = false;
			this.opos = this.pos = null; // Clear temp variables
			return false;
			
		},
		drag: function(e) {

			if ($.browser.msie && !e.button) return this.stop.apply(this, [e]); // check for IE mouseup when moving into the document again
			var o = this.options;
			
			this.pos = $.ui.getPointer(e); //relative mouse position
			//We can stop here if it's not a actual new position (FF issue)
			if(this.rpos && this.rpos[0] == this.pos[0] && this.rpos[1] == this.pos[1]) return false;
			this.rpos = [this.pos[0],this.pos[1]]; //absolute mouse position
			
			if(o.pp) { //If we have a positioned parent, use a relative position
				this.pos[0] -= o.po.left;
				this.pos[1] -= o.po.top;	
			}
			
			if( (Math.abs(this.rpos[0]-this.opos[0]) > o.preventionDistance || Math.abs(this.rpos[1]-this.opos[1]) > o.preventionDistance) && this.init == false) //If position is more than x pixels from original position, start dragging
				this.start.apply(this,[e]);			
			else {
				if(this.init == false) return false;
			}
		
			if(o._drag) o._drag.apply(this.element, [this.helper, this.pos, o.cursorAt, this]);
			return false;
			
		}
	});

 })($);
 
 
(function($) {

	$.fn.draggable = function(o) {
		return this.each(function() {
			new $.ui.draggable(this,o);	
		});
	};
	
	$.ui.ddmanager = {
		current: null,
		droppables: [],
		prepareOffsets: function(that) {
			
			var m = $.ui.ddmanager.droppables;
			for(var i=0;i<m.length;i++) {
				m[i].offset = $(m[i].item.element).offset({ border: false });
				if(that) { //Activate the droppable if used directly from draggables
					if(m[i].item.options.accept(that)) m[i].item.activate.call(m[i].item);
				}
			}
						
		},
		prepareOffsetsAsync: function(that) {

			var m = $.ui.ddmanager.droppables; var ml = m.length; var j = 0; var i= 0;
			
			var func = (function() {
				for(;i<ml;i++) {
					m[i].offset = $(m[i].item.element).offsetLite({ border: false });
					if(that) { //Activate the droppable if used directly from draggables
						if(m[i].item.options.onActivate && m[i].item.options.accept(that)) m[i].item.activate.call(m[i].item);
					}
					
					if(i == j*20+19) { //Call the next block of 20
						j++;
						var c = arguments.callee;
						window.setTimeout(function() { c(); }, 0);
						break;
					}
				}
			})();

		},
		fire: function(that) {
			
			var m = $.ui.ddmanager.droppables;
			for(var i=0;i<m.length;i++) {
				if(!m[i].offset) continue;
				if($.ui.intersect(that, m[i], m[i].item.options.tolerance)) {
					m[i].item.drop.call(m[i].item);
				}
				if(m[i].item.options.accept(that)) m[i].item.deactivate.call(m[i].item);
			}
						
		},
		update: function(that) {
			
			var m = $.ui.ddmanager.droppables;
			for(var i=0;i<m.length;i++) {
				if(!m[i].offset) continue;
				if($.ui.intersect(that, m[i], m[i].item.options.tolerance)) {
					if(m[i].over == 0) { m[i].out = 0; m[i].over = 1; m[i].item.hover.call(m[i].item); }
				} else {
					if(m[i].out == 0) { m[i].out = 1; m[i].over = 0; m[i].item.out.call(m[i].item); }
				}
				
			}
						
		}
	};
	
	
	$.ui.draggable = function(el,o) {
		
		var options = {};
		$.extend(options, o);
		$.extend(options, {
			_start: function(h,p,c,t) {
				self.start.apply(t, [self]); // Trigger the onStart callback				
			},
			_beforeStop: function(h,p,c,t) {
				self.stop.apply(t, [self]); // Trigger the onStart callback
			},
			_stop: function(h,p,c,t) {
				var o = t.options;
				if(o.stop) o.stop.apply(t.element, [t.helper, t.pos, o.cursorAt, t]);
			},
			_drag: function(h,p,c,t) {
				self.drag.apply(t, [self]); // Trigger the onStart callback
			}			
		});
		var self = this;
		
		if(options.ghosting == true) options.helper = 'clone'; //legacy option check
		this.interaction = new $.ui.mouseInteraction(el,options);
		
		if(options.name) $.ui.add(options.name, 'draggable', this); //Append to UI manager if a name exists as option
		
	};
	
	$.extend($.ui.draggable.prototype, {
		plugins: {},
		pos: null,
		opos: null,
		currentTarget: null,
		lastTarget: null,
		helper: null,
		timer: null,
		slowMode: false,
		element: null,
		init: false,
		execPlugins: function(type,self) {
			var o = self.options;
			if(this.plugins[type]) {
				for(var i=0;i<this.plugins[type].length;i++) {
					if(self.options[this.plugins[type][i][0]]) {
						this.plugins[type][i][1].call(self, this);
					}
							
				}	
			}			
		},
		start: function(that) {
			
			var o = this.options;
			$.ui.ddmanager.current = this;
			
			that.execPlugins('start', this);
			
			if(this.slowMode && $.ui.droppable && !o.dropBehaviour)
				$.ui.ddmanager.prepareOffsets(this);
				
			if(o.start) o.start.apply(this.element, [this.helper, this.pos, o.cursorAt, this]);
			
			return false;
						
		},
		stop: function(that) {			
			
			var o = this.options;
			
			that.execPlugins('stop', this);

			if(this.slowMode && $.ui.droppable && !o.dropBehaviour) //If cursorAt is within the helper, we must use our drop manager
				$.ui.ddmanager.fire(this);

			return false;
			
		},
		drag: function(that) {

			var o = this.options;

			if(this.slowMode && $.ui.droppable && !o.dropBehaviour) // If cursorAt is within the helper, we must use our drop manager to look where we are
				$.ui.ddmanager.update(this);

			this.pos = [this.pos[0]-(o.cursorAt.left ? o.cursorAt.left : 0), this.pos[1]-(o.cursorAt.top ? o.cursorAt.top : 0)];
			that.execPlugins('drag', this);

			if(o.drag) var nv = o.drag.apply(this.element, [this.helper, this.pos, o.cursorAt, this]);
			var nl = (nv && nv.x) ? nv.x :  this.pos[0];
			var nt = (nv && nv.y) ? nv.y :  this.pos[1];
			
			$(this.helper).css('left', nl+'px').css('top', nt+'px'); // Stick the helper to the cursor
			return false;
			
		}
	});

 })($);
 
 
(function($) {

	$.ui.plugin("draggable", "stop", "effect", function() {
	
		if(this.options.effect[1]) {
			if(this.helper != this.element) {
				this.options.beQuietAtEnd = true;
				switch(this.options.effect[1]) {
					case 'fade':
						$(this.helper).fadeOut(300, function() { $(this).remove(); });
						break;
					default:
						$(this.helper).remove();
						break;	
				}
				
			}
		}
		
	});
	
	$.ui.plugin("draggable", "start", "effect", function() {
	
		if(this.options.effect[0]) {

			switch(this.options.effect[0]) {
				case 'fade':
					$(this.helper).hide().fadeIn(300);
					break;
			}

		}
		
	});

//----------------------------------------------------------------

	$.ui.plugin("draggable", "start", "zIndex", function() {
		if($(this.helper).css("zIndex")) this.options.ozIndex = $(this.helper).css("zIndex");
		$(this.helper).css('zIndex', this.options.zIndex);
	});
	
	$.ui.plugin("draggable", "stop", "zIndex", function() {
		if(this.options.ozIndex)
			$(this.helper).css('zIndex', this.options.ozIndex);
	});
	
//----------------------------------------------------------------

	$.ui.plugin("draggable", "start", "opacity", function() {
		if($(this.helper).css("opacity")) this.options.oopacity = $(this.helper).css("opacity");
		$(this.helper).css('opacity', this.options.opacity);
	});
	
	$.ui.plugin("draggable", "stop", "opacity", function() {
		if(this.options.oopacity)
			$(this.helper).css('opacity', this.options.oopacity);
	});
	
//----------------------------------------------------------------

	$.ui.plugin("draggable", "stop", "revert", function() {
	
		var rpos = { left: 0, top: 0 };
		var o = this.options;
		o.beQuietAtEnd = true;
		if(this.helper != this.element) {
			
			rpos = $(this.sorthelper || this.element).offset({ border: false });

			var nl = rpos.left-o.po.left-o.margins.left;
			var nt = rpos.top-o.po.top-o.margins.top;

		} else {
			var nl = o.curOffset.left - (o.po ? o.po.left : 0);
			var nt = o.curOffset.top - (o.po ? o.po.top : 0);
		}
		
		var self = this;

		$(this.helper).animate({
			left: nl,
			top: nt
		}, 500, function() {
			
			if(o.wasPositioned)
				$(self.element).css('position', o.wasPositioned);
				
			if(o.onStop) o.onStop.apply(self, [self.element, self.helper, self.pos, [o.curOffset.left - o.po.left,o.curOffset.top - o.po.top],self]);
			
			//Using setTimeout because of strange flickering in Firefox
			if(self.helper != self.element) window.setTimeout(function() { $(self.helper).remove(); }, 0);
			
		});
		
	});
	
//----------------------------------------------------------------

	$.ui.plugin("draggable", "start", "iframeFix", function() {
		if(!this.slowMode) { // Make clones on top of iframes (only if we are not in slowMode)
			if(this.options.iframeFix.constructor == Array) {
				for(var i=0;i<this.options.iframeFix.length;i++) {
					var curOffset = $(this.options.iframeFix[i]).offset({ border: false });
					$("<div class='DragDropIframeFix' style='background: #fff;'></div>").css("width", $(this.options.iframeFix[i])[0].offsetWidth+"px").css("height", $(this.options.iframeFix[i])[0].offsetHeight+"px").css("position", "absolute").css("opacity", "0.001").css("z-index", "1000").css("top", curOffset.top+"px").css("left", curOffset.left+"px").appendTo("body");
				}		
			} else {
				$("iframe").each(function() {					
					var curOffset = $(this).offset({ border: false });
					$("<div class='DragDropIframeFix' style='background: #fff;'></div>").css("width", this.offsetWidth+"px").css("height", this.offsetHeight+"px").css("position", "absolute").css("opacity", "0.001").css("z-index", "1000").css("top", curOffset.top+"px").css("left", curOffset.left+"px").appendTo("body");
				});							
			}		
		}

	});
	
	$.ui.plugin("draggable","stop", "iframeFix", function() {
		if(this.options.iframeFix) $("div.DragDropIframeFix").each(function() { this.parentNode.removeChild(this); }); //Remove frame helpers	
	});
	
//----------------------------------------------------------------

	$.ui.plugin("draggable", "start", "containment", function() {

		var o = this.options;
		if(o.containment == 'parent') o.containment = this.element.parentNode;

		if(o.cursorAtIgnore) { //Get the containment
			if(o.containment.left == undefined) {
				
				if(o.containment == 'document') {
					o.containment = {
						top: 0-o.margins.top,
						left: 0-o.margins.left,
						right: $(document).width()-o.margins.right,
						bottom: ($(document).height() || document.body.parentNode.scrollHeight)-o.margins.bottom
					}	
				} else { //I'm a node, so compute top/left/right/bottom
					
					var conEl = $(o.containment)[0];
					var conOffset = $(o.containment).offset({ border: false });
	
					o.containment = {
						top: conOffset.top-o.margins.top,
						left: conOffset.left-o.margins.left,
						right: conOffset.left+(conEl.offsetWidth || conEl.scrollWidth)-o.margins.right,
						bottom: conOffset.top+(conEl.offsetHeight || conEl.scrollHeight)-o.margins.bottom
					}	
				
				}
				
			}
		}

	});
	
	$.ui.plugin("draggable", "drag", "containment", function() {
		
		var o = this.options;
		if(o.cursorAtIgnore) {
			if((this.pos[0] < o.containment.left-o.po.left)) this.pos[0] = o.containment.left-o.po.left;
			if((this.pos[1] < o.containment.top-o.po.top)) this.pos[1] = o.containment.top-o.po.top;
			if(this.pos[0]+$(this.helper)[0].offsetWidth > o.containment.right-o.po.left) this.pos[0] = o.containment.right-o.po.left-$(this.helper)[0].offsetWidth;
			if(this.pos[1]+$(this.helper)[0].offsetHeight > o.containment.bottom-o.po.top) this.pos[1] = o.containment.bottom-o.po.top-$(this.helper)[0].offsetHeight;
		}
		
	});
	
//----------------------------------------------------------------

	$.ui.plugin("draggable", "drag", "grid", function() {

		var o = this.options;
		if(o.cursorAtIgnore) {
			this.pos[0] = o.curOffset.left + o.margins.left - o.po.left + Math.round((this.pos[0] - o.curOffset.left - o.margins.left + o.po.left) / o.grid[0]) * o.grid[0];
			this.pos[1] = o.curOffset.top + o.margins.top - o.po.top + Math.round((this.pos[1] - o.curOffset.top - o.margins.top + o.po.top) / o.grid[1]) * o.grid[1];
		}

	});

//----------------------------------------------------------------

	$.ui.plugin("draggable", "drag", "axis", function(d) {
		
		var o = this.options;
		if(o.constraint) o.axis = o.constraint; //Legacy check
		if(o.cursorAtIgnore) {
			switch(o.axis) {
				case "x":
					this.pos[1] = o.curOffset.top - o.margins.top - o.po.top; break;
				case "y":
					this.pos[0] = o.curOffset.left - o.margins.left - o.po.left; break;
			}
		}
		
	});

//----------------------------------------------------------------

	$.ui.plugin("draggable", "drag", "scroll", function() {
		
		var o = this.options;
		o.scrollSensitivity	= o.scrollSensitivity != undefined ? o.scrollSensitivity : 20;
		o.scrollSpeed		= o.scrollSpeed != undefined ? o.scrollSpeed : 20;

		if(o.pp && o.ppOverflow) { // If we have a positioned parent, we only scroll in this one
			// TODO: Extremely strange issues are waiting here..handle with care
		} else {
			if((this.rpos[1] - $(window).height()) - $(document).scrollTop() > -o.scrollSensitivity) window.scrollBy(0,o.scrollSpeed);
			if(this.rpos[1] - $(document).scrollTop() < o.scrollSensitivity) window.scrollBy(0,-o.scrollSpeed);
			if((this.rpos[0] - $(window).width()) - $(document).scrollLeft() > -o.scrollSensitivity) window.scrollBy(o.scrollSpeed,0);
			if(this.rpos[0] - $(document).scrollLeft() < o.scrollSensitivity) window.scrollBy(-o.scrollSpeed,0);
		}
		
	});

//----------------------------------------------------------------

	$.ui.plugin("draggable", "drag", "wrapHelper", function() {

		var o = this.options;
		if(!o.cursorAtIgnore) {

			if(!o.pp || !o.ppOverflow) {
				var wx = $(window).width() - ($.browser.mozilla ? 20 : 0);
				var sx = $(document).scrollLeft();
				
				var wy = $(window).height();
				var sy = $(document).scrollTop();	
			} else {
				var wx = o.pp.offsetWidth + o.po.left - 20;
				var sx = o.pp.scrollLeft;
				
				var wy = o.pp.offsetHeight + o.po.top - 20;
				var sy = o.pp.scrollTop;						
			}

			this.pos[0] -= ((this.rpos[0]-o.cursorAt.left - wx + this.helper.offsetWidth+o.margins.right) - sx > 0 || (this.rpos[0]-o.cursorAt.left+o.margins.left) - sx < 0) ? (this.helper.offsetWidth+o.margins.left+o.margins.right - o.cursorAt.left * 2) : 0;
			
			this.pos[1] -= ((this.rpos[1]-o.cursorAt.top - wy + this.helper.offsetHeight+o.margins.bottom) - sy > 0 || (this.rpos[1]-o.cursorAt.top+o.margins.top) - sy < 0) ? (this.helper.offsetHeight+o.margins.top+o.margins.bottom - o.cursorAt.top * 2) : 0;

		}

	});

})(jQuery);