
(function($) {
	$.fn.draggable = function(options) {
		options = $.extend({
			beforeDrag: function(e) {
				var position, delta;
				//if cursorAt then the element is positioned at cursor position
				if (options.cursorAt) {
					position = {
						x: $.DDM.pointer.x + this.DB.extraOffset.x,
						y: $.DDM.pointer.y + this.DB.extraOffset.y
					}
				} else {
					delta = {
						x: $.DDM.pointer.x - this.DB.pointer.x ,
						y: $.DDM.pointer.y - this.DB.pointer.y
					}

					//apply grid
					if (this.DB.grid) {
						delta = this.DB.applyGrid(delta);
					}
					//if there are limits then recalculate delta
					if (this.DB.limitOffset) {
						delta = {
							x: Math.max(
								this.DB.limitOffset.x,
								Math.min(
									this.DB.position.x + delta.x,
									this.DB.limitOffset.x + this.DB.limitOffset.w - this.DB.size.wb
								)) - this.DB.position.x,
							y: Math.max(
								this.DB.limitOffset.y,
								Math.min(
									this.DB.position.y + delta.y,
									this.DB.limitOffset.y + this.DB.limitOffset.h - this.DB.size.hb
								))-this.DB.position.y
						};
						
					}
					position = {
						x: this.DB.offset.x + delta.x,
						y: this.DB.offset.y + delta.y
					};
				}
				if (this.DB.dragModifier) {
					position = this.DB.dragModifier(position);
				}
				this.DB.onDrag.apply(this.DB.draggedEls, [this.DB.proxy||this.DB.draggedEls, position]);
				$(this.DB.proxy||this.DB.draggedEls).css({
					left: position.x + 'px',
					top: position.y + 'px'
				});
				return false;
			},
			beforeStartDrag: function() {
				//get element position, offset position and size
				this.DB.position = $.iUtil.getPosition(this.DB.draggedEls);
				this.DB.size = $.iUtil.getSize(this.DB.draggedEls);
				this.DB.offset = {
					x: this.DB.draggedEls.offsetLeft,
					y: this.DB.draggedEls.offsetTop
				};
				/*this.DB.offset = {
					x: parseInt($.curCSS(this.DB.draggedEls, 'left'), 10)||0,
					y: parseInt($.curCSS(this.DB.draggedEls, 'top'), 10)||0
				};*/
				//if cursorAt then calculate the extra offset
				if (this.DB.cursorAt) {
					this.DB.extraOffset = {
						x: this.DB.cursorAt.left ?
							(this.DB.cursorAt.left * (-1))
							: this.DB.cursorAt.right ?
								(- this.DB.size.wb + this.DB.cursorAt.right)
								: 0,
						y: this.DB.cursorAt.top ?
							(this.DB.cursorAt.top * (-1))
							: this.DB.cursorAt.bottom ?
								(- this.DB.size.hb + this.DB.cursorAt.bottom)
								: 0
					};
				}
				//if containment then calculates the limits
				if (this.DB.containment) {
					//if a node then get node position and size and calculate limits
					if (this.DB.containment.parentNode) {
						this.DB.limitOffset = $.extend(
							$.iUtil.getPosition(this.DB.containment),
							$.iUtil.getSize(this.DB.containment)
						);
						this.DB.limitOffset.h = this.DB.limitOffset.hb;
						this.DB.limitOffset.w = this.DB.limitOffset.wb;
					//if document then get document size
					} else if(this.DB.containment === 'document') {
						var clientScroll = $.iUtil.getScroll();
						this.DB.limitOffset = {
							x: 0,
							y: 0,
							h: Math.max(clientScroll.h,clientScroll.ih),
							w: Math.max(clientScroll.w,clientScroll.iw)
						};
					//if viewport then get document size and scroll
					} else if(this.DB.containment === 'viewport') {
						var clientScroll = $.iUtil.getScroll();
						this.DB.limitOffset = {
							x: clientScroll.l,
							y: clientScroll.t,
							h: Math.min(clientScroll.h,clientScroll.ih),
							w: Math.min(clientScroll.w,clientScroll.iw)
						};
					} else {
						this.DB.limitOffset = this.DB.containment;
					}
				}
				var el = this.DB.proxy||this.DB.draggedEls;
				
				//store old zIndex value to restore later
				if (options.zIndex) {
					this.DB.oldZIndex = $.attr(el, 'zIndex');
					el.style.zIndex = 'number' == typeof options.zIndex ? options.zIndex : 1999;
				}
				
				el.style.display = '';
				this.DB.beforeDrag.apply(this);
			},
			startDrag: function() {
				this.DB.onStart.apply(this.DB.draggedEls, [this.DB.proxy||this.DB.draggedEls, $.DDM.dragged.DB.targets]);
				return false;
			},
			//get pointer (overides the default fonction because of the axis option)
			getPointer: function(e){
				return {
					x : this.DB.axis === 'y' ? this.DB.pointer.x : e.pageX,
					y : this.DB.axis === 'x' ? this.DB.pointer.y : e.pageY
				};
			},
			beforeStopDrag: function() {
				var handledByUser = this.DB.onStop.apply(
					this.DB.draggedEls,
					[
						this.DB.proxy||this.DB.draggedEls,
						this.DB.revert ?
							this.DB.offset :
							(
								this.DB.proxy ?
									{x:this.DB.proxy.offsetLeft,y:this.DB.proxy.offsetTop}
									:
									{x:this.DB.draggedEls.offsetLeft, y:this.DB.draggedEls.offsetTop}
							)
					]);
				//if used chooses not to handle the stop dragging action then clear proxy and position teh element
				if (handledByUser === false) {
					if (this.DB.revert) {
						$(this.DB.draggedEls).css({
							left: this.DB.offset.x + 'px',
							top: this.DB.offset.y + 'px'
						});
					}
					if(this.DB.proxy) {
						if (!this.DB.revert) {
							$(this.DB.draggedEls).css({
								left: this.DB.proxy.offsetLeft + 'px',
								top: this.DB.proxy.offsetTop + 'px'
							});
						}
						$(this.DB.proxy).remove();
					}
				}
				//reverse to the old zIndex
				if (options.zIndex) {
					this.DB.draggedEls.style.zIndex = this.DB.oldZIndex;
				}
				return false;
			},
			getDraggedEls: function(el) {
				//find element that needs to be dragged
				var del = el.DB.toDrag||el,
					isAllowed = true;
				//if the event was fired by a illegal element or condition then stop the dragging
				if ('function' == typeof options.dragPrevention) {
					isAllowed = options.dragPrevention.apply(del,[$.DDM.currentTarget]);
				} else if ('string' == typeof options.dragPrevention) {
					var chunks = options.dragPrevention.toUpperCase().split(',');
					jQuery.each(
						chunks,
						function() {
							if ($.DDM.currentTarget.nodeName == this){
								isAllowed=false
							}
						}
					);
				}
				if (isAllowed == true) {
					//if proxy is required add it to the DOM
					if(options.ghostly || options.helper === 'clone') {
						if (options.helper == 'clone') {
							options.ghostly = true;
						}
						el.DB.proxy = $(del).clone(true).insertAfter(del).hide()[0];
					} else if (options.helper) {
						el.DB.proxy = $(options.helper.apply(del)).hide()[0];
					}
					if (el.DB.proxy) {
						$(el.DB.proxy).css({
							top: $.curCSS(del, 'top'),
							left: $.curCSS(del, 'left'),
							display: 'none'
						});
					}
					return del;
				}
				return;
			},
			//apply grid to current position
			applyGrid: function(delta) {
				return {
					x: parseInt((delta.x + (this.grid.x* delta.x/Math.abs(delta.x))/2)/this.grid.x, 10) * this.grid.x,
					y: parseInt((delta.y + (this.grid.y* delta.y/Math.abs(delta.y))/2)/this.grid.y, 10) * this.grid.y
				};
			},
			onStart: function(){return false;},
			onStop: function(){return false;},
			onDrag: function(){return false;}
		}, options||{});
		
		return this.each(function(){
			var el = $(this);
			//find the handle
			var toDrag = this;
			if (options.handle) {
				el = $(options.handle, this);
				if (el.size() == 0 )
					el = this;
			}
			
			if (options.preventionDistance) {
				options.snap = options.preventionDistance;
			}
			
			//iterate each element and add drag behavior
			el.each(function(){
				if (!this.DB) {
					$.DDM.drag(this, options);
					if (options.handle) this.DB.toDrag = toDrag;
				}
			});
		});
	};
 })(jQuery);