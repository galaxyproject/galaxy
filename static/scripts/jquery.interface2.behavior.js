
(function($) {
	//drag and drop manager
	$.DDM = {
		
		//define a new draggable behavior
		drag: function(el, options) {
			el.DB = new $.dragBehavior(el, options);
		},
		
		//define a new droppable behavior
		drop: function(el, options) {
			el.DrB = new $.dropBehavior(el, options);
		},
		
		//drop targets
		targets: [],
		
		//current pointer position
		pointer: null,
		
		shiftKey: false,
		altKey: false,
		ctrlKey: false,
		
		//dragged element/elements
		dragged: null,
		
		//timeout holder
		preventionTimeout: null,
		
		mouseMove: function(e) {
			if (!$.DDM.dragged) {
				return false;
			}
			if (e) {
				//store current event target
				$.DDM.currentTarget = e.target;
				
				//store pointer position
				$.DDM.pointer = $.DDM.dragged.DB.getPointer.apply($.DDM.dragged,[e]);
				$.DDM.shiftKey = e.shiftKey;
				$.DDM.altKey = e.altKey;
				$.DDM.ctrlKey = e.ctrlKey;
			}
			
			//if the pointer was not moved enough do not start the dragging action
			if (!$.DDM.dragged.DB.dragThreshMet) {
				var snap = Math.max(
					Math.abs($.DDM.pointer.x - $.DDM.dragged.DB.pointer.x),
					Math.abs($.DDM.pointer.y - $.DDM.dragged.DB.pointer.y)
				);
				if (snap >= $.DDM.dragged.DB.snap) {
					return $.DDM.startDrag(e);
				}
				return;
			}
			
			$.DDM.dragged.DB.beforeDrag.apply($.DDM.dragged, [e]);
			var toReturn = $.DDM.dragged.DB.drag.apply($.DDM.dragged, [e]);
			
			//checks if dragged element validates against drop targets
			if ($.DDM.dragged.DB.hasTargets) {
				for (var i=0; i< $.DDM.dragged.DB.targets.length; i++) {
					$.DDM.dragged.DB.targets[i].DrB.checkTarget.apply($.DDM.dragged.DB.targets[i], [e]);
				}
			}
			
			if (toReturn === false) {
				return false;
			}
			return;
		},
		
		mouseUp: function(e) {
			if (!$.DDM.dragged)
				return;
			$.DDM.currentTarget = e.target;
			var toReturn = true;
			var dragged = $.DDM.dragged ;
			clearTimeout($.DDM.preventionTimeout);
			
			//if the dragging action started
			if (dragged.DB.dragThreshMet) {
				dragged.DB.beforeStopDrag.apply(dragged,[e]);
				toReturn = dragged.DB.stopDrag.apply(dragged,[e]);
			} else {
			    if(dragged.DB.proxy) { $(dragged.DB.proxy).remove(); }
			    dragged.DB.onClickOnly.apply(dragged,[e]);
			}
			
			$.DDM.clearTargets(e);
			$.DDM.clearOptions();
			
			$(document).unbind('mousemove', $.DDM.mouseMove);
			$(document).unbind('mouseup', $.DDM.mouseUp);
			
			return toReturn;
		},
		//start the dragging action
		startDrag: function(e) {
			if (!$.DDM.dragged)
				return;
			$.DDM.dragged.DB.dragThreshMet = true;
			clearTimeout($.DDM.preventionTimeout );
			$.DDM.dragged.DB.beforeStartDrag.apply($.DDM.dragged, [e]);

			return $.DDM.dragged.DB.startDrag.apply($.DDM.dragged, [e]);
		},
		
		//check the drop targets and validate if are posibile targets for current dragged element
		findTargets: function() {
			$.DDM.dragged.DB.targets = [];
			for( var i=0; i< $.DDM.targets.length; i++) {
				for (var j in $.DDM.targets[i].DrB.groups) {
					if ($.DDM.dragged.DB.groups[j] && $.DDM.targets[i].DrB.isTarget.apply($.DDM.targets[i])) {
						$.DDM.targets[i].DrB.onActivate.apply($.DDM.targets[i]);
						$.DDM.dragged.DB.targets[$.DDM.dragged.DB.targets.length] = $.DDM.targets[i];
						break;
					}
				}
			}
			$.DDM.dragged.DB.hasTargets = ($.DDM.dragged.DB.targets.length>0) ;
		},
		
		//clear the previously activated drop targets
		clearTargets: function(e) {
			for (var i=0; i< $.DDM.dragged.DB.targets.length; i++) {
				$.DDM.dragged.DB.targets[i].DrB.onDeactivate.apply($.DDM.dragged.DB.targets[i], [e]);
			}
			$.DDM.dragged.DB.targets = [];
			$.DDM.dragged.DB.hasTargets = false;
		},
		
		//clear all options stored in the dragging action
		clearOptions: function() {
			$.DDM.currentTarget = null;
			$.DDM.dragged.DB.dragThreshMet = false;
			$.DDM.dragged.DB.draggedEls = null;
			$.DDM.dragged = null;
		}
	};
	
	//drag behavior object
	$.dragBehavior = function(el, options) {
		this.init(el, options);
	};
	
	$.dragBehavior.prototype = {
		draggedEls: null,
		groups: {'default':true},
		size: null,
		offset: null,
		pointer: null,
		proxy: null,
		dragThreshMet: false,
		preventionTimeout: 400,
		beforeStartDrag: function(){},
		getPointer: function(e){return {x:e.pageX,y:e.pageY}},
		startDrag: function() {},
		beforeDrag: function(){},
		drag: function(){},
		beforeStopDrag: function(){},
		stopDrag: function(){},
		targets: [],
		hasTargets: false,
		snap: 0,
		getDraggedEls: function(el) {
			return el;
		},
		init: function(el, options) {
			$(el).bind('mousedown', this.mouseDown);
			$.extend(this, options);
			el.onselectstart = function(){return false;};
			el.ondrag = function(){return false;};
			el.unselectable = "on";
		},
		
		mouseDown: function(e) {
			if (!this.DB) {
				return false;
			}
			$(document).bind('mousemove', $.DDM.mouseMove);
			$(document).bind('mouseup', $.DDM.mouseUp);
			$.DDM.currentTarget = e.target;
			$.DDM.shiftKey = e.shiftKey;
			$.DDM.altKey = e.altKey;
			$.DDM.ctrlKey = e.ctrlKey;
			this.DB.draggedEls = this.DB.getDraggedEls(this, e);
			if (!this.DB.draggedEls) {
				return;
			}
			$.DDM.dragged = this;
			$.DDM.dragged.DB.dragThreshMet = false;
			$.DDM.dragged.DB.pointer = $.DDM.pointer = {x:e.pageX, y:e.pageY};
			$.DDM.findTargets();
			if (this.DB.preventionTimeout) {
				$.DDM.preventionTimeout = setTimeout(function(){$.DDM.startDrag(e)}, this.DB.preventionTimeout);
				return false;
			}
			if (this.DB.snap) {
				return false;
			}
			return $.DDM.startDrag(e);
		}
	};
	//drop behavior object
	$.dropBehavior = function(el, options) {
		this.init(el, options);
	};
	$.dropBehavior.prototype = {
		isTarget: function() {return false},
		onActivate: function(){},
		onDeactivate: function(){},
		checkTarget: function() {return false},
		onHover: function(){},
		onOut: function(){},
		onDrop: function(){},
		position: null,
		size: null,
		tolerance: 'pointer',
		groups: {'default':true},
		isOver: false,
		init: function(el, options) {
			$.DDM.targets[$.DDM.targets.length] = el;
			$.extend(this, options);
		}
	};
	
 })(jQuery);