// dependencies
define([], function() {

// frame manager
var View = Backbone.View.extend({
    // defaults inputs
    options: {
        // default frame size
        frame: {
            cols : 6,
            rows : 3
        },

        // maximum number of rows
        rows: 1000,
       
        // cell size in px
        cell: 130,
       
        // margin
        margin: 5,
        
        // scroll speed
        scroll: 5,
        
        // minimum top
        top_min: 40,
        
        // maximum number of frames
        frame_max: 9,
        
        // visible
        visible: true,
        
        // onchange
        onchange: null
    },
    
    // number of columns
    cols: 0,
    
    // scroll/element top
    top: 0,
    
    // viewport scrolling state
    top_max: 0,
    
    // frame z-index
    frame_z : 0,
    
    // frame counter
    frame_counter: 0,
    
    // frame counter
    frame_counter_id: 0,
    
    // frame list
    frame_list: [],
    
    // frame shadow
    frame_shadow: null,
    
    // frame panel visible
    visible: null,
    
    // initialize
    initialize : function(options) {
        // add to masthead menu
        var self = this;
        
        // read in defaults
        if (options) {
            this.options = _.defaults(options, this.options);
        }
        
        // set visibility
        this.visible = this.options.visible;
        
        // initialize top
        this.top = this.top_max = this.options.top_min;
        
        // create
        this.setElement(this._template());
        
        // load background
        $(this.el).append(this._templateBackground());
        
        // load menu buttons
        $(this.el).append(this._templateMenu());
        
        // load to main frame
        $(this.el_main).append($(this.el));

        //
        // define shadow frame
        //
        var id_shadow = '#frame-shadow';

        // add shadow template
        $(this.el).append(this._templateShadow(id_shadow.substring(1)));

        // initialize frame
        this.frame_shadow = {
            id              : id_shadow,
            screen_location : {},
            grid_location   : {},
            grid_rank       : null,
            grid_lock       : false
        };
        
        // initialize size
        this._frameResize(this.frame_shadow, {width: 0, height: 0});
        
        // add shadow to frame list
        this.frame_list[id_shadow] = this.frame_shadow;
        
        // initialize panel
        this._panelRefresh();
       
        // apply visibility
        if (!this.visible) {
            this.hide();
        } else {
            this.show();
        }
        
        // catch window resize event
        var self = this;
        $(window).resize(function () {
            if (self.visible)
                self._panelRefresh();
        });
    },
    
    /**
     * Adds and displays a new frame.
     *
     * options:
     *  type: 'url' or 'other' ; if 'url', 'content' is treated as a URL and loaded into an iframe; 
     *        if 'other', content is treated as a function or raw HTML. content function is passed a single 
     *        argument that is the frame's content DOM element
     *  content: the content to be loaded into the frame.
     */
    add: function(options) {
        // frame default options
        var frameOptions = {
            title: '',
            content: null,
            target: '',
            type: null
        }
        
        // read in defaults
        if (options) {
            options = _.defaults(options, frameOptions);
        } else {
            options = frameOptions;
        }
    
        // check for content
        if(!options.content) {
            return;
        }
        
        // check for number of frames
        if (this.frame_counter >= this.options.frame_max) {
            alert("You have reached the maximum number of allowed frames (" + this.options.frame_max + ").");   
            return;
        }

        // generate frame identifier
        var frame_id = '#frame-' + (this.frame_counter_id++);

        // check if frame exists
        if ($(frame_id).length !== 0) {
            alert("This frame already exists. This page might contain multiple frame managers.");
            return;
        }
        
        // reset top
        this.top = this.options.top_min;

        // append
        var $frame_el = null;
        if (options.type === 'url') {
            $frame_el = $(this._templateFrameUrl(frame_id.substring(1), options.title, options.content));
        } else if (options.type === 'other') {
            $frame_el = $(this._templateFrame(frame_id.substring(1), options.title));

            // Load content into frame.
            var content_elt = $frame_el.find('.f-content');
            if (_.isFunction(options.content)) {
                options.content(content_elt);
            }
            else {
                content_elt.append(options.content);
            }
        }
        $(this.el).append($frame_el);
        
        // construct a new frame
        var frame = {
            id              : frame_id,
            screen_location : {},
            grid_location   : {},
            grid_rank       : null,
            grid_lock       : false
        };
        
        // set dimensions
        options.width   = this._toPixelCoord('width', this.options.frame.cols);
        options.height  = this._toPixelCoord('height', this.options.frame.rows);
        
        // default z-index
        this.frame_z = parseInt($(frame.id).css('z-index'));
        
        // add to frame list
        this.frame_list[frame_id] = frame;

        // increase frame counter
        this.frame_counter++;

        // resize
        this._frameResize(frame, {width: options.width, height: options.height});
       
        // place frame
        this._frameInsert(frame, {top: 0, left: 0}, true);
            
        // show frames if hidden
        if (!this.visible) {
            this.show();
        }
    },
    
    // show panel
    show: function() {
        // show
        this.visible = true;
        
        // show
        this.$el.find(".frame").fadeIn('fast');
        
        // hide shadow
        this.$el.find(this.frame_shadow.id).hide();
    
        // show background
        this.$el.find(".frame-background").show();
        
        // show panel
        this._panelRefresh();
        
        // refresh
        this._menuRefresh();
    },
    
    // hide panel
    hide: function() {
        // make sure that no event is currently processing
        if (this.event.type !== null)
            return;
              
        // hide
        this.visible = false;
        
        // hide 
        this.$el.find(".frame").fadeOut('fast');
        
        // hide background
        this.$el.find(".frame-background").hide();
        
        // hide menu
        this.$el.find(".frame-menu").hide();
        
        // refresh
        this._menuRefresh();
    },

    // length
    length: function() {
        return this.frame_counter;
    },
    
    // set onchange event
    setOnChange: function(callback) {
        this.options.onchange = callback;
    },
    
    /*
        EVENT HANDLING
    */
    
    // event
    event: {
        type    : null,
        target  : null,
        xy      : null
    },
    
    // events
    events: {
        // global frame events
        'mousemove'                         : '_eventFrameMouseMove',
        'mouseup'                           : '_eventFrameMouseUp',
        'mouseleave'                        : '_eventFrameMouseUp',
        'mousewheel'                        : '_eventPanelScroll',
        'DOMMouseScroll'                    : '_eventPanelScroll',
                
        // events fixed to elements
        'mousedown .frame'                  : '_eventFrameMouseDown',
        'mousedown .frame-background'       : '_eventHide',
        'mousedown .frame-scroll-up'        : '_eventPanelScroll_up',
        'mousedown .frame-scroll-down'      : '_eventPanelScroll_down',
        'mousedown .f-close'                : '_eventFrameClose',
        'mousedown .f-pin'                  : '_eventFrameLock'
    },

    // drag start
    _eventFrameMouseDown: function (e) {
        // skip if event is already active
        if (this.event.type !== null) {
            return;
        }
        
        // check for drag event
        if ($(e.target).hasClass('f-header') || $(e.target).hasClass('f-title')) {
            this.event.type = 'drag';
        }
        
        // check for resize event
        if ($(e.target).hasClass('f-resize')) {
            this.event.type = 'resize';
        }
        
        // skip if no event has to be handled
        if (this.event.type === null) {
            return;
        }

        // prevent
        e.preventDefault();
            
        // identify frame
        this.event.target = this._frameIdentify(e.target);
       
        // check if frame is locked
        if (this.event.target.grid_lock) {
            this.event.type = null;
            return;
        }
        
        // backup event details
        this.event.xy = {
            x: e.originalEvent.pageX,
            y: e.originalEvent.pageY
        };
            
        // prepare drag/resize
        this._frameDragStart(this.event.target);
    },

    // mouse move event
    _eventFrameMouseMove: function (e) {
        // check
        if (this.event.type != 'drag' && this.event.type != 'resize') {
            return;
        }
            
        // current position
        var event_xy_new = {
            x : e.originalEvent.pageX,
            y : e.originalEvent.pageY
        };
            
        // position delta
        var event_xy_delta = {
            x : event_xy_new.x - this.event.xy.x,
            y : event_xy_new.y - this.event.xy.y
        };
        
        // update
        this.event.xy = event_xy_new;

        // object position / size
        var p = this._frameScreen (this.event.target);
        
        // resize event
        if (this.event.type == 'resize') {
            // update
            p.width  += event_xy_delta.x;
            p.height += event_xy_delta.y;
            
            // check size
            var min_dim = this.options.cell - this.options.margin - 1;
            p.width = Math.max(p.width, min_dim);
            p.height = Math.max(p.height, min_dim);
            
            // apply resize to frame
            this._frameResize(this.event.target, p);
            
            // break down to grid coordinates
            p.width = this._toGridCoord('width', p.width) + 1;
            p.height = this._toGridCoord('height', p.height) + 1;
            
            // transfer back to pixels
            p.width = this._toPixelCoord('width', p.width);
            p.height = this._toPixelCoord('height', p.height);
        
            // apply
            this._frameResize(this.frame_shadow, p);
        
            // fix position
            this._frameInsert(this.frame_shadow, {
                top     : this._toGridCoord('top', p.top),
                left    : this._toGridCoord('left', p.left)
            });
        }
                 
        // drag event
        if (this.event.type == 'drag') {
            // update
            p.left  += event_xy_delta.x;
            p.top   += event_xy_delta.y;
            
            // apply
            this._frameOffset(this.event.target, p);

            // get location of shadow
            var l = {
                top     : this._toGridCoord('top', p.top),
                left    : this._toGridCoord('left', p.left)
            };
       
            // increase priority of current frame
            if (l.left !== 0) {
                l.left++;
            }
            
            // fix position
            this._frameInsert(this.frame_shadow, l);
        }
    },
    
    // mouse up
    _eventFrameMouseUp: function (e) {
        // check
        if (this.event.type != 'drag' && this.event.type != 'resize') {
            return;
        }
            
        // stop
        this._frameDragStop(this.event.target);
        
        // reset event
        this.event.type = null;
    },
    
    // drag start
    _eventFrameClose: function (e) {
        // check
        if (this.event.type !== null) {
            return;
        }
        
        // prevent
        e.preventDefault();

        // get frame
        var frame = this._frameIdentify(e.target);
        var self  = this;
        
        // fade out
        $(frame.id).fadeOut('fast', function() {
            // remove element
            $(frame.id).remove();
            
            // remove from dictionary
            delete self.frame_list[frame.id];
            
            // reduce frame counter
            self.frame_counter--;
            
            // reload
            self._panelRefresh(true);
            
            // refresh scroll state once all animations completed
            self._panelAnimationComplete();
            
            // hide if no frames left
            if (self.visible && self.frame_counter == 0)
                self.hide();
        });
    },
    
    // drag start
    _eventFrameLock: function (e) {
        // check
        if (this.event.type !== null) {
            return;
        }
        
        // prevent
        e.preventDefault();

        // get frame
        var frame = this._frameIdentify(e.target);
        
        // check
        if (frame.grid_lock) {
            // unlock
            frame.grid_lock = false;
            
            // remove class
            $(frame.id).find('.f-pin').removeClass('toggle');
            $(frame.id).find('.f-header').removeClass('f-not-allowed');
            $(frame.id).find('.f-title').removeClass('f-not-allowed');
            $(frame.id).find('.f-resize').show();
            $(frame.id).find('.f-close').show();
        } else {
            // lock
            frame.grid_lock = true;
            
            // add class
            $(frame.id).find('.f-pin').addClass('toggle');
            $(frame.id).find('.f-header').addClass('f-not-allowed');
            $(frame.id).find('.f-title').addClass('f-not-allowed');
            $(frame.id).find('.f-resize').hide();
            $(frame.id).find('.f-close').hide();
        }
    },

    // show/hide panel
    _eventHide: function (e) {
        // check
        if (this.event.type !== null) {
            return;
        }

        // hide panel
        this.hide();
    },
    
    /**
     * Fired when scrolling occurs on panel.
     */
    _eventPanelScroll: function(e) {
        // check
        if (this.event.type !== null || !this.visible) {
            return;
        }

        // Stop propagation if scrolling is happening inside a frame.
        // TODO: could propagate scrolling if at top/bottom of frame.
        var frames = $(e.srcElement).parents('.frame')
        if (frames.length !== 0) {
            e.stopPropagation();
            return;
        }

        // prevent
        e.preventDefault();

        // get wheel delta
        var delta = e.originalEvent.detail ? e.originalEvent.detail : e.originalEvent.wheelDelta / -3;
        
        // refresh panel
        this._panelScroll(delta);
    },
    
    // scroll up
    _eventPanelScroll_up: function(e) {
        // check
        if (this.event.type !== null)
            return;
  
        // prevent
        e.preventDefault();

        // scroll up
        this._panelScroll(-this.options.scroll);
    },
    
    // scroll down
    _eventPanelScroll_down: function(e) {
        // check
        if (this.event.type !== null)
            return;
     
        // prevent
        e.preventDefault();
        
        // scroll down
        this._panelScroll(this.options.scroll);
    },
    
    /*
        FRAME EVENTS SUPPORT
    */
    
    // identify
    _frameIdentify: function(target) {
        return this.frame_list['#' + $(target).closest('.frame').attr('id')];
    },

    // drag start
    _frameDragStart : function (frame) {
        // set focus
        this._frameFocus(frame, true);
            
        // get current dimensions
        var p = this._frameScreen (frame);
        
        // initialize shadow
        this._frameResize(this.frame_shadow, p);
        this._frameGrid(this.frame_shadow, frame.grid_location);
        
        // reset location
        frame.grid_location = null;
        
        // show shadow
        $(this.frame_shadow.id).show();
        
        // load frame cover
        $('.f-cover').show();
    },
    
    // drag stop
    _frameDragStop : function (frame) {
        // remove focus
        this._frameFocus(frame, false);
        
        // get new dimensions
        var p = this._frameScreen(this.frame_shadow);
        
        // update frame
        this._frameResize(frame, p);
        this._frameGrid(frame, this.frame_shadow.grid_location, true);
        
        // reset location of shadow
        this.frame_shadow.grid_location = null;

        // hide shadow
        $(this.frame_shadow.id).hide();
        
        // hide frame cover
        $('.f-cover').hide();
        
        // refresh scroll state once all animations completed
        this._panelAnimationComplete();
    },
    
    /*
        GRID/PIXEL CONVERTER
    */
    
    // converts a pixel coordinate to grids
    _toGridCoord: function (type, px) {
        // determine sign
        var sign = (type == 'width' || type == 'height') ? 1 : -1;
        
        if (type == 'top') px -= this.top;
        
        // return
        return parseInt((px + sign * this.options.margin) / this.options.cell, 10);
    },
    
    // converts a grid coordinate to pixels
    _toPixelCoord: function (type, g) {
        // determine sign
        var sign = (type == 'width' || type == 'height') ? 1 : -1;
        
        // return
        var px = (g * this.options.cell) - sign * this.options.margin;
        
        if (type == 'top') px += this.top;
        
        return px;
    },
    
    // get grid coordinates
    _toGrid: function (px) {
        // full set
        return {
            top     : this._toGridCoord('top', px.top),
            left    : this._toGridCoord('left', px.left),
            width   : this._toGridCoord('width', px.width),
            height  : this._toGridCoord('height', px.height)
        };
    },
       
    // get pixel coordinates
    _toPixel: function(g) {
        return {
            top     : this._toPixelCoord('top', g.top),
            left    : this._toPixelCoord('left', g.left),
            width   : this._toPixelCoord('width', g.width),
            height  : this._toPixelCoord('height', g.height)
        };
    },

    /* 
        COLLISION DETECTION
    */
    
    // check collision
    _isCollision: function(g) {
        // is collision pair
        function is_collision_pair (a, b) {
            return !(a.left > b.left + b.width - 1 || a.left + a.width - 1 < b.left ||
                     a.top > b.top + b.height  - 1 || a.top + a.height - 1 < b.top);
        }
        
        // search
        for (var i in this.frame_list) {
            // get frame
            var frame = this.frame_list[i];

            // skip
            if (frame.grid_location === null)
                continue;

            // check if g collides with frame
            if (is_collision_pair (g, frame.grid_location))
                return true;
        }
       
        // return
        return false;
    },
    
    // location/grid rank
    _locationRank: function(loc) {
        return (loc.top * this.cols) + loc.left;
    },
    
    /*
        ONSCREEN MENU
    */
    
    // update frame counter
    _menuRefresh: function() {
        // scroll up possible?
        if (this.visible) {
            if (this.top == this.options.top_min)
                $(".frame-scroll-up").hide();
            else
                $(".frame-scroll-up").show();
            
            // scroll down possible?
            if (this.top == this.top_max)
                $(".frame-scroll-down").hide();
            else
                $(".frame-scroll-down").show();
        }
        
        // trigger onchange
        if (this.options.onchange) {
            this.options.onchange();
        }
    },
    
    /*
        PANEL/WINDOW FUNCTIONS
    */

    // panel on animation complete / frames not moving
    _panelAnimationComplete: function() {
        var self = this;
        $(".frame").promise().done(function() {self._panelScroll(0, true)});
    },

    // refresh panel
    _panelRefresh: function(animate) {
        // get current size
        this.cols = parseInt($(window).width() / this.options.cell, 10) + 1;
        
        // recalculate frame positions
        this._frameInsert(null, null, animate);
    },
    
    // update scroll
    _panelScroll: function(delta, animate) {
        // new top value
        var top_new = this.top - this.options.scroll * delta;

        // update top
        top_new = Math.max(top_new, this.top_max);
        top_new = Math.min(top_new, this.options.top_min);
            
        // update screen if necessary
        if (this.top != top_new) {
            // update screen
            for (var i in this.frame_list) {
                // get frame
                var frame = this.frame_list[i];

                // skip
                if (frame.grid_location !== null) {
                    var screen_location = {
                        top  : frame.screen_location.top - (this.top - top_new),
                        left : frame.screen_location.left
                    }
                    this._frameOffset(frame, screen_location, animate);
                }
            }
            
            // update top value
            this.top = top_new;
        }
        
        // refresh
        this._menuRefresh();
    },
    
    /*
        FRAME FUNCTIONS
    */
      
    // frame insert at given location
    _frameInsert: function(frame, new_loc, animate) {
        // define
        var place_list = [];
       
        // frame to place
        if (frame) {
            // reset grid location
            frame.grid_location = null;
            
            // set first one to be placed
            place_list.push([frame, this._locationRank(new_loc)]);
        }
        
        // search
        var i = null;
        for (i in this.frame_list) {
            // get frame
            var f = this.frame_list[i];

            // check
            if (f.grid_location !== null && !f.grid_lock) {
                // reset grid location
                f.grid_location = null;
                
                // set up for placement
                place_list.push([f, f.grid_rank]);
            }
        }

        // sort place list by rank
        place_list.sort(function(a, b) {
            var i = a[1];
            var j = b[1];
            return i < j ? -1 : (i > j ? 1 : 0);
        });
                
        // place
        for (i = 0; i < place_list.length; i++) {
            this._framePlace(place_list[i][0], animate);
        }
        
        // identify maximum viewport size
        this.top_max = 0;
        for (var i in this.frame_list) {
            // get frame
            var frame = this.frame_list[i];

            // skip
            if (frame.grid_location !== null)
                this.top_max = Math.max(this.top_max, frame.grid_location.top + frame.grid_location.height);
        }
        
        // mesh maximum top with window size and margin
        this.top_max = $(window).height() - this.top_max * this.options.cell - 2 * this.options.margin;
        
        // fix value
        this.top_max = Math.min(this.top_max, this.options.top_min);
        
        // panel menu
        this._menuRefresh();
    },

    // naive frame place
    _framePlace: function(frame, animate) {
        // reset grid location
        frame.grid_location = null;
        
        // grid coordinates of new frame
        var g = this._toGrid(this._frameScreen(frame));
        
        // try grid coordinates
        var done = false;
        for (var i = 0; i < this.options.rows; i++) {
            // ensure that the first grid column is checked despite limited window space
            for (var j = 0; j < Math.max(1, this.cols - g.width); j++) {
                // coordinates
                g.top   = i;
                g.left  = j;
       
                // no collision
                if (!this._isCollision(g)) {
                    done = true;
                    break;
                }
            }
       
            // break
            if (done) {
                break;
            }
        }
        
        // check if valid spot was found
        if (done) {
            this._frameGrid(frame, g, animate);
        } else {
            console.log("Grid dimensions exceeded.");
        }
    },
    
    // focus
    _frameFocus: function(frame, has_focus) {
        // get new z-value
        var z = this.frame_z + (has_focus ? 1 : 0);
        
        // update
        $(frame.id).css('z-index', z);
    },
    
    // new left/top position frame
    _frameOffset: function(frame, p, animate) {
        // update screen location
        frame.screen_location.left = p.left;
        frame.screen_location.top = p.top;
                
        // animate
        if (animate) {
            // set focus on animated
            this._frameFocus(frame, true);
            
            // prepare for callback
            var self = this;
            
            // animate and remove focus
            $(frame.id).animate({top: p.top, left: p.left}, 'fast', function()
            {
                // remove focus
                self._frameFocus(frame, false);
            });
        } else
            // update css
            $(frame.id).css({top: p.top, left: p.left});
    },

    // resize frame
    _frameResize: function(frame, p) {
        // update css
        $(frame.id).css({width: p.width, height: p.height});
    
        // update descriptor
        frame.screen_location.width = p.width;
        frame.screen_location.height = p.height;
    },

    // new grid location
    _frameGrid: function (frame, l, animate) {
        // update grid location
        frame.grid_location = l;

        // place frame
        this._frameOffset(frame, this._toPixel(l), animate);
            
        // update grid rank
        frame.grid_rank = this._locationRank(l);
    },
    
    // get frame dimensions
    _frameScreen: function(frame) {
        var p = frame.screen_location;
        return {top: p.top, left: p.left, width: p.width, height: p.height};
    },
    
    /*
        HTML TEMPLATES
    */
    
    // main element
    _template: function() {
        return  '<div class="galaxy-frame"></div>';
    },
    
    // fill regular frame template
    _templateFrame: function(id, title) {
        // check title
        if (!title)
            title = '';

        // load template
        return  '<div id="' + id + '" class="frame corner">' +
                    '<div class="f-header corner">' +
                        '<span class="f-title">' + title + '</span>' +
                        '<span class="f-icon f-close fa fa-trash-o"></span>' +
                        '<span class="f-icon f-pin fa fa-thumb-tack"></span>' +
                    '</div>' +
                    '<div class="f-content">' +
                        '<div class="f-cover"></div>' +
                    '</div>' +
                    '<span class="f-resize f-icon corner fa fa-resize-full"></span>' +
                '</div>';
    },
    
    // fill regular frame template
    _templateFrameUrl: function(id, title, url) {
        // url
        if (url.indexOf('?') == -1)
            url += '?';
        else
            url += '&';
        url += 'widget=True';
        
        // element
        var $el = $(this._templateFrame(id, title));
        $el.find('.f-content').append('<iframe scrolling="auto" class="f-iframe" src="' + url + '"></iframe>');
        
        // load template
        return $el;
    },
    
    // fill shadow template
    _templateShadow: function(id) {
        return '<div id="' + id + '" class="frame-shadow corner"></div>';
    },
    
    // fill background template in order to cover underlying iframes
    _templateBackground: function() {
        return '<div class="frame-background"></div>';
    },
    
    // fill menu button template
    _templateMenu: function() {
        return  '<div class="frame-scroll-up frame-menu fa fa-chevron-up fa-2x"></div>' +
                '<div class="frame-scroll-down frame-menu fa fa-chevron-down fa-2x"></div>';
    }
});

// return
return {
    View: View
};

});
