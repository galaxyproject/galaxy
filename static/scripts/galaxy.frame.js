/*
    galaxy frames v2.0
*/

// dependencies
define(["utils/galaxy.css", "libs/backbone/backbone-relational"], function(css) {
       

// frame manager
var GalaxyFrameManager = Backbone.View.extend(
{
    // base element
    el: '#everything',
    
    // master head
    el_header : '#masthead',
    
    // defaults inputs
    options:
    {
        // default frame size
        frame:
        {
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
        frame_max: 10
    },
    
    // number of columns
    cols: 0,
    
    // scroll/element top
    top: 0,
    
    // maximum viewport
    top_max: 0,
    
    // frame counter
    frame_counter: 0,
    
    // frame counter
    frame_counter_id: 0,
    
    // frame list
    frame_list: [],
    
    // frame shadow
    galaxy_frame_shadow: null,
    
    // frame panel visible
    visible: false,
    
    // frame active/disabled
    active: false,
    
    // initialize
    initialize : function(options)
    {
        // load required css files
        css.load_file(options.url.styles + "/galaxy.frame.css");
        
        // read in defaults
        if (options)
            this.options = _.defaults(options, this.options);
        
        // initialize top
        this.top = this.top_max = this.options.top_min;
        
        // load background
        $(this.el).append(this.frame_template_background());
        
        // load menu buttons
        $(this.el).append(this.frame_template_menu());
        
        // load load button
        $(this.el_header).append(this.frame_template_header());
        
        //
        // define shadow frame
        //
        var id_shadow = '#galaxy-frame-shadow';

        // add shadow template
        $(this.el).append(this.frame_template_shadow(id_shadow.substring(1)));

        // initialize frame
        this.galaxy_frame_shadow = {
            id              : id_shadow,
            screen_location : {},
            grid_location   : {},
            grid_rank       : null,
            grid_lock       : false
        };
        
        // initialize size
        this.frame_resize(this.galaxy_frame_shadow, {width: 0, height: 0});
        
        // add shadow to frame list
        this.frame_list[id_shadow] = this.galaxy_frame_shadow;
        
        // initialize panel
        this.panel_refresh();
        
        // link events
        this.event_initialize();

        // add
        $(".galaxy-frame-active").tooltip({title: "Enable/Disable Scratchbook"});
        $(".galaxy-frame-load").tooltip({title: "Show/Hide Scratchbook"});

        // catch window resize event
        var self = this;
        $(window).resize(function ()
        {
            self.panel_refresh();
        });
        
        // catch window close
        window.onbeforeunload = function()
        {
            if (self.frame_counter > 0)
                return "You opened " + self.frame_counter + " frame(s) which will be lost.";
        };
    },
    
    // check for mobile devices
    is_mobile: function()
    {
        return navigator.userAgent.match(/mobile|(iPad)|(iPhone)|(iPod)|(android)|(webOS)/i);
    },
    
    /*
        EVENT HANDLING
    */
    
    // event
    event:
    {
        type    : null,
        target  : null,
        xy      : null
    },
    
    // events
    event_initialize: function()
    {
        /*if (!this.is_mobile())
        {*/
            this.events = {
                // global page events
                'mousemove'                                 : 'event_frame_mouse_move',
                'mouseup'                                   : 'event_frame_mouse_up',
                'mouseleave'                                : 'event_frame_mouse_up',
                'mousewheel'                                : 'event_panel_scroll',
                'DOMMouseScroll'                            : 'event_panel_scroll',
                
                // events fixed to elements
                'mousedown .galaxy-frame'                   : 'event_frame_mouse_down',
                'mousedown .galaxy-frame-active'            : 'event_panel_active',
                'mousedown .galaxy-frame-load'              : 'event_panel_load',
                'mousedown .galaxy-frame-background'        : 'event_panel_load',
                'mousedown .galaxy-frame-scroll-up'         : 'event_panel_scroll_up',
                'mousedown .galaxy-frame-scroll-down'       : 'event_panel_scroll_down',
                'mousedown .f-close'                        : 'event_frame_close',
                'mousedown .f-pin'                          : 'event_frame_lock'
            };
        /*} else {
            this.events = {
                'touchstart'                            : 'event_frame_mouse_down',
                'touchstart .f-close'                   : 'event_frame_close',
                'touchstart .f-pin'                     : 'event_frame_lock',
                'touchmove'                             : 'event_frame_mouse_move',
                'touchend'                              : 'event_frame_mouse_up',
                'touchleave'                            : 'event_mouse_up',
                'touchstart .galaxy-frame-load'         : 'event_frame_load'
            };
        };*/
        
        // delegate
        this.delegateEvents(this.events);
    },

    // drag start
    event_frame_mouse_down: function (e)
    {
        // skip if event is already active
        if (this.event.type !== null)
            return;
        
        // check for drag event
        if ($(e.target).hasClass('f-header') ||
            $(e.target).hasClass('f-title'))
            this.event.type = 'drag';
        
        // check for resize event
        if ($(e.target).hasClass('f-resize'))
            this.event.type = 'resize';
        
        // skip if no event has to be handled
        if (this.event.type === null)
            return;

        // prevent
        e.preventDefault();
            
        // identify frame
        this.event.target = this.event_get_frame(e.target);
       
        // check if frame is locked
        if (this.event.target.grid_lock)
        {
            this.event.type = null;
            return;
        }
        
        // backup event details
        this.event.xy = {x: e.originalEvent.pageX, y: e.originalEvent.pageY};
            
        // prepare drag/resize
        this.frame_drag_start(this.event.target);
    },

    // mouse move event
    event_frame_mouse_move: function (e)
    {
        // check
        if (this.event.type != 'drag' && this.event.type != 'resize')
            return;
            
        // current position
        var event_xy_new = {x: e.originalEvent.pageX , y: e.originalEvent.pageY};
            
        // position delta
        var event_xy_delta =
        {
            x : event_xy_new.x - this.event.xy.x,
            y : event_xy_new.y - this.event.xy.y
        };
        
        // update
        this.event.xy = event_xy_new;

        // object position / size
        var p = this.frame_screen (this.event.target);
        
        // resize event
        if (this.event.type == 'resize')
        {
            // update
            p.width  += event_xy_delta.x;
            p.height += event_xy_delta.y;
            
            // check size
            var min_dim = this.options.cell - this.options.margin - 1;
            p.width = Math.max(p.width, min_dim);
            p.height = Math.max(p.height, min_dim);
            
            // apply resize to frame
            this.frame_resize(this.event.target, p);
            
            // break down to grid coordinates
            p.width = this.to_grid_coord('width', p.width) + 1;
            p.height = this.to_grid_coord('height', p.height) + 1;
            
            // transfer back to pixels
            p.width = this.to_pixel_coord('width', p.width);
            p.height = this.to_pixel_coord('height', p.height);
        
            // apply
            this.frame_resize(this.galaxy_frame_shadow, p);
        
            // fix position
            this.frame_insert(this.galaxy_frame_shadow, {
                top     : this.to_grid_coord('top', p.top),
                left    : this.to_grid_coord('left', p.left)
            });
        }
                 
        // drag event
        if (this.event.type == 'drag')
        {
            // update
            p.left  += event_xy_delta.x;
            p.top   += event_xy_delta.y;
            
            // apply
            this.frame_offset(this.event.target, p);

            // get location of shadow
            var l = {
                top     : this.to_grid_coord('top', p.top),
                left    : this.to_grid_coord('left', p.left)
            };
       
            // increase priority of current frame
            if (l.left !== 0)
                l.left++;
            
            // fix position
            this.frame_insert(this.galaxy_frame_shadow, l);
        }
    },
    
    // mouse up
    event_frame_mouse_up: function (e)
    {
        // check
        if (this.event.type != 'drag' && this.event.type != 'resize')
            return;
            
        // stop
        this.frame_drag_stop(this.event.target);
        
        // reset event
        this.event.type = null;
    },
    
    // drag start
    event_frame_close: function (e)
    {
        // check
        if (this.event.type !== null)
            return;
        
        // prevent
        e.preventDefault();

        // get frame
        var frame = this.event_get_frame(e.target);
        var self  = this;
        
        // fade out
        $(frame.id).fadeOut('fast', function()
        {
            // remove element
            $(frame.id).remove();
            
            // remove from dictionary
            delete self.frame_list[frame.id];
            
            // reduce frame counter
            self.frame_counter--;
            
            // reload
            self.panel_refresh(true);
            
            // refresh scroll state once all animations completed
            self.panel_animation_complete();
            
            // hide if no frames left
            if (self.visible && self.frame_counter == 0)
                self.panel_show_hide();
        });
    },
    
    // drag start
    event_frame_lock: function (e)
    {
        // check
        if (this.event.type !== null)
            return;
        
        // prevent
        e.preventDefault();

        // get frame
        var frame = this.event_get_frame(e.target);
        
        // check
        if (frame.grid_lock)
        {
            // unlock
            frame.grid_lock = false;
            
            // remove class
            $(frame.id).find('.f-pin').removeClass('f-toggle');
            $(frame.id).find('.f-header').removeClass('f-not-allowed');
            $(frame.id).find('.f-title').removeClass('f-not-allowed');
            $(frame.id).find('.f-resize').show();
            $(frame.id).find('.f-close').show();
        } else {
            // lock
            frame.grid_lock = true;
            
            // add class
            $(frame.id).find('.f-pin').addClass('f-toggle');
            $(frame.id).find('.f-header').addClass('f-not-allowed');
            $(frame.id).find('.f-title').addClass('f-not-allowed');
            $(frame.id).find('.f-resize').hide();
            $(frame.id).find('.f-close').hide();
        }
    },

    // show/hide panel
    event_panel_load: function (e)
    {
        // check
        if (this.event.type !== null)
            return;
        
        // prevent
        e.preventDefault();

        // load panel
        this.panel_show_hide();
    },
    
    // activate/disable panel
    event_panel_active: function (e)
    {
        // check
        if (this.event.type !== null)
            return;
        
        // prevent
        e.preventDefault();

        // load panel
        this.panel_active_disable();
    },
    
    // scroll
    event_panel_scroll: function(e)
    {
        // check
        if (this.event.type !== null || !this.visible)
            return;
            
        // prevent
        e.preventDefault();

        // get wheel delta
        var delta = e.originalEvent.detail ? e.originalEvent.detail : e.originalEvent.wheelDelta / -3;
        
        // refresh panel
        this.panel_scroll(delta);
    },
    
    // scroll up
    event_panel_scroll_up: function(e)
    {
        // check
        if (this.event.type !== null)
            return;
  
        // prevent
        e.preventDefault();

        // scroll up
        this.panel_scroll(-this.options.scroll);
    },
    
    // scroll down
    event_panel_scroll_down: function(e)
    {
        // check
        if (this.event.type !== null)
            return;
     
        // prevent
        e.preventDefault();
        
        // scroll down
        this.panel_scroll(this.options.scroll);
    },
    
    // identify
    event_get_frame: function(target)
    {
        return this.frame_list['#' + $(target).closest('.galaxy-frame').attr('id')];
    },
    
    /*
        FRAME EVENTS START/STOP
    */
    
    // drag start
    frame_drag_start : function (frame)
    {
        // set focus
        this.frame_focus(frame, true);
            
        // get current dimensions
        var p = this.frame_screen (frame);
        
        // initialize shadow
        this.frame_resize(this.galaxy_frame_shadow, p);
        this.frame_grid(this.galaxy_frame_shadow, frame.grid_location);
        
        // reset location
        frame.grid_location = null;
        
        // show shadow
        $(this.galaxy_frame_shadow.id).show();
        
        // load frame cover
        $('.f-cover').show();
    },
    
    // drag stop
    frame_drag_stop : function (frame)
    {
        // remove focus
        this.frame_focus(frame, false);
        
        // get new dimensions
        var p = this.frame_screen(this.galaxy_frame_shadow);
        
        // update frame
        this.frame_resize(frame, p);
        this.frame_grid(frame, this.galaxy_frame_shadow.grid_location, true);
        
        // reset location of shadow
        this.galaxy_frame_shadow.grid_location = null;

        // hide shadow
        $(this.galaxy_frame_shadow.id).hide();
        
        // hide frame cover
        $('.f-cover').hide();
        
        // refresh scroll state once all animations completed
        this.panel_animation_complete();
    },
    
    /*
        GRID/PIXEL CONVERTER
    */
    
    // converts a pixel coordinate to grids
    to_grid_coord: function (type, px)
    {
        // determine sign
        var sign = (type == 'width' || type == 'height') ? 1 : -1;
        
        if (type == 'top') px -= this.top;
        
        // return
        return parseInt((px + sign * this.options.margin) / this.options.cell, 10);
    },
    
    // converts a grid coordinate to pixels
    to_pixel_coord: function (type, g)
    {
        // determine sign
        var sign = (type == 'width' || type == 'height') ? 1 : -1;
        
        // return
        var px = (g * this.options.cell) - sign * this.options.margin;
        
        if (type == 'top') px += this.top;
        
        return px;
    },
    
    // get grid coordinates
    to_grid: function (px)
    {
        // full set
        return {
            top     : this.to_grid_coord('top', px.top),
            left    : this.to_grid_coord('left', px.left),
            width   : this.to_grid_coord('width', px.width),
            height  : this.to_grid_coord('height', px.height)
        };
    },
       
    // get pixel coordinates
    to_pixel: function(g)
    {
        return {
            top     : this.to_pixel_coord('top', g.top),
            left    : this.to_pixel_coord('left', g.left),
            width   : this.to_pixel_coord('width', g.width),
            height  : this.to_pixel_coord('height', g.height)
        };
    },

    /* 
        COLLISION DETECTION
    */
    
    // check collision
    is_collision: function(g)
    {
        // is collision pair
        function is_collision_pair (a, b)
        {
            return !(a.left > b.left + b.width - 1 || a.left + a.width - 1 < b.left ||
                     a.top > b.top + b.height  - 1 || a.top + a.height - 1 < b.top);
        }
        
        // search
        for (var i in this.frame_list)
        {
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
    location_rank: function(loc)
    {
        return (loc.top * this.cols) + loc.left;
    },
    
    /*
        ONSCREEN MENU
    */
    
    // update frame counter
    menu_refresh: function()
    {
        // update on screen counter
        $(".galaxy-frame-load .number").text(this.frame_counter);
    
        // check
        if(this.frame_counter == 0)
            $(".galaxy-frame-load").hide();
        else
            $(".galaxy-frame-load").show();
            
        // scroll up possible?
        if (this.top == this.options.top_min)
            $(".galaxy-frame-scroll-up").hide();
        else
            $(".galaxy-frame-scroll-up").show();
        
        // scroll down possible?
        if (this.top == this.top_max)
            $(".galaxy-frame-scroll-down").hide();
        else
            $(".galaxy-frame-scroll-down").show();
    },
    
    /*
        PANEL/WINDOW FUNCTIONS
    */

    // panel on animation complete / frames not moving
    panel_animation_complete: function()
    {
        var self = this;
        $(".galaxy-frame").promise().done(function() {self.panel_scroll(0, true)});
    },

    // refresh panel
    panel_refresh: function(animate)
    {
        // get current size
        this.cols = parseInt($(window).width() / this.options.cell, 10) + 1;
        
        // recalculate frame positions
        this.frame_insert(null, null, animate);
    },
    
    // update scroll
    panel_scroll: function(delta, animate)
    {
        // new top value
        var top_new = this.top - this.options.scroll * delta;

        // update top
        top_new = Math.max(top_new, this.top_max);
        top_new = Math.min(top_new, this.options.top_min);
            
        // update screen if necessary
        if (this.top != top_new)
        {
            // update screen
            for (var i in this.frame_list)
            {
                // get frame
                var frame = this.frame_list[i];

                // skip
                if (frame.grid_location !== null)
                {
                    var screen_location = {
                        top  : frame.screen_location.top - (this.top - top_new),
                        left : frame.screen_location.left
                    }
                    this.frame_offset(frame, screen_location, animate);
                }
            }
            
            // update top value
            this.top = top_new;
        }
        
        // refresh
        this.menu_refresh();
    },
    
    // show or hide panel
    panel_show_hide: function()
    {           
        // check
        if (this.visible)
        {
            // hide
            this.visible = false;
            
            // hide 
            $(".galaxy-frame").fadeOut('fast');
            
            // add class
            $(".galaxy-frame-load .icon").addClass("fa-icon-eye-close");
            $(".galaxy-frame-load .icon").removeClass("fa-icon-eye-open");
            
            // hide background
            $(".galaxy-frame-background").hide();
            
            // hide menu
            $(".galaxy-frame-menu").hide();
        } else {
            // show
            this.visible = true;
            
            // show
            $(".galaxy-frame").fadeIn('fast');
            
            // add class
            $(".galaxy-frame-load .icon").addClass("fa-icon-eye-open");
            $(".galaxy-frame-load .icon").removeClass("fa-icon-eye-close");
            
            // hide shadow
            $(this.galaxy_frame_shadow.id).hide();
        
            // show background
            $(".galaxy-frame-background").show();
            
            // show menu
            this.menu_refresh();
        }
    },
    
    // show or hide panel
    panel_active_disable: function()
    {
        // check
        if (this.active)
        {
            // disable
            this.active = false;
            
            // untoggle
            $(".galaxy-frame-active .icon").removeClass("f-toggle");

            // hide panel
            if (this.visible)
                this.panel_show_hide();
        } else {
            // activate
            this.active = true;
            
            // toggle
            $(".galaxy-frame-active .icon").addClass("f-toggle");
        }
    },
    
    /*
        FRAME FUNCTIONS
    */
    // adds and displays a new frame/window
    frame_new: function(options)
    {
        // validate
        if (!this.active)
        {
            // load frame in main window
            if (options.location == 'center')
            {
                var galaxy_main = $( window.parent.document ).find( 'iframe#galaxy_main' );
                galaxy_main.attr( 'src', options.content );
            } else
                window.location = options.content;

            // stop
            return;
        }

        // check for number of frames
        if (this.frame_counter > this.options.frame_max)
        {
            alert("You have reached the maximum number of allowed frames (" + this.options.frame_max + ").");   
            return;   
        }

        // generate frame identifier
        var frame_id = '#galaxy-frame-' + (this.frame_counter_id++);

        // check if frame exists
        if ($(frame_id).length !== 0)
        {
            alert("This frame already exists. This page might contain multiple frame managers.");
            return;
        }
        
        // reset top
        this.top = this.options.top_min;

        // append
        $(this.el).append(this.frame_template(frame_id.substring(1), options.title, options.type, options.content));
            
        // construct a new frame
        var frame = {
            id              : frame_id,
            screen_location : {},
            grid_location   : {},
            grid_rank       : null,
            grid_lock       : false
        };
        
        // set dimensions
        options.width   = this.to_pixel_coord('width', this.options.frame.cols);
        options.height  = this.to_pixel_coord('height', this.options.frame.rows);
        
        // add to frame list
        this.frame_list[frame_id] = frame;

        // increase frame counter
        this.frame_counter++;

        // resize
        this.frame_resize(frame, {width: options.width, height: options.height});
       
        // place frame
        this.frame_insert(frame, {top: 0, left: 0}, true);
            
        // show frames if hidden
        if (!this.visible)
            this.panel_show_hide();
    },
      
    // frame insert at given location
    frame_insert: function(frame, new_loc, animate)
    {
        // define
        var place_list = [];
       
        // frame to place
        if (frame)
        {
            // reset grid location
            frame.grid_location = null;
            
            // set first one to be placed
            place_list.push([frame, this.location_rank(new_loc)]);
        }
        
        // search
        var i = null;
        for (i in this.frame_list)
        {
            // get frame
            var f = this.frame_list[i];

            // check
            if (f.grid_location !== null && !f.grid_lock)
            {
                // reset grid location
                f.grid_location = null;
                
                // set up for placement
                place_list.push([f, f.grid_rank]);
            }
        }

        // sort place list by rank
        place_list.sort(function(a, b)
        {
            var i = a[1];
            var j = b[1];
            return i < j ? -1 : (i > j ? 1 : 0);
        });
                
        // place
        for (i = 0; i < place_list.length; i++)
            this.frame_place(place_list[i][0], animate);
        
        // identify maximum viewport size
        this.top_max = 0;
        for (var i in this.frame_list)
        {
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
        this.menu_refresh();
    },

    // naive frame place
    frame_place: function(frame, animate)
    {
        // reset grid location
        frame.grid_location = null;
        
        // grid coordinates of new frame
        var g = this.to_grid(this.frame_screen(frame));
        
        // try grid coordinates
        var done = false;
        for (var i = 0; i < this.options.rows; i++)
        {
            // ensure that the first grid column is checked despite limited window space
            for (var j = 0; j < Math.max(1, this.cols - g.width); j++)
            {
                // coordinates
                g.top   = i;
                g.left  = j;
       
                // no collision
                if (!this.is_collision(g))
                {
                    done = true;
                    break;
                }
            }
       
            // break
            if (done)
                break;
        }
        
        // check if valid spot was found
        if (done)
            this.frame_grid(frame, g, animate);
        else
            console.log("Grid dimensions exceeded.");
    },
    
    // focus
    frame_focus: function(frame, has_focus)
    {
        // get new z-value
        var z = parseInt(css.get_attribute('galaxy-frame', 'z-index')) + (has_focus ? 1 : 0);
        
        // update
        $(frame.id).css('z-index', z);
    },
    
    // new left/top position frame
    frame_offset: function(frame, p, animate)
    {
        // update screen location
        frame.screen_location.left = p.left;
        frame.screen_location.top = p.top;
                
        // animate
        if (animate)
        {
            // set focus on animated
            this.frame_focus(frame, true);
            
            // prepare for callback
            var self = this;
            
            // animate and remove focus
            $(frame.id).animate({top: p.top, left: p.left}, 'fast', function()
            {
                // remove focus
                self.frame_focus(frame, false);
            });
        } else
            // update css
            $(frame.id).css({top: p.top, left: p.left});
    },

    // resize frame
    frame_resize: function(frame, p)
    {
        // update css
        $(frame.id).css({width: p.width, height: p.height});
    
        // update descriptor
        frame.screen_location.width = p.width;
        frame.screen_location.height = p.height;
    },

    // new grid location
    frame_grid: function (frame, l, animate)
    {
        // update grid location
        frame.grid_location = l;

        // place frame
        this.frame_offset(frame, this.to_pixel(l), animate);
            
        // update grid rank
        frame.grid_rank = this.location_rank(l);
    },
    
    // get frame dimensions
    frame_screen: function(frame)
    {   
        var p = frame.screen_location;
        return {top: p.top, left: p.left, width: p.width, height: p.height};
    },
    
    /*
        HTML TEMPLATES
    */
    
    // fill regular frame template
    frame_template: function(id, title, type, content)
    {
        // check title
        if (!title)
            title = '';

        // identify content type
        if (type == 'url')
            content = '<iframe scrolling="auto" class="f-iframe"  src="' + content + '"></iframe>';
        
        // load template
        return  '<div id="' + id + '" class="galaxy-frame f-corner">' +
                    '<div class="f-header f-corner">' +
                        '<span class="f-title">' + title + '</span>' +
                        '<span class="f-icon f-pin fa-icon-pushpin"></span>' +
                        '<span class="f-icon f-close fa-icon-trash"></span>' +            
                    '</div>' +
                    '<div class="f-content f-corner">' + content +
                        '<div class="f-cover"></div>' +
                    '</div>' +
                    '<span class="f-resize f-icon f-corner fa-icon-resize-full"></span>' +
                '</div>';
    },
    
    // fill shadow template
    frame_template_shadow: function(id)
    {
        return '<div id="' + id + '" class="galaxy-frame-shadow f-corner"></div>';
    },
    
    // fill background template in order to cover underlying iframes
    frame_template_background: function()
    {
        return '<div class="galaxy-frame-background"></div>';
    },
    
    // fill load button template
    frame_template_header: function()
    {
        return  '<div class="galaxy-frame-load f-corner">' +
                   '<div class="number f-corner">0</div>' +
                   '<div class="icon fa-icon-2x"></div>' +
                '</div>' +
                '<div class="galaxy-frame-active f-corner" style="position: absolute; top: 8px;">' +
                   '<div class="icon fa-icon-2x fa-icon-th"></div>' +
                '</div>';
    },
    
    // fill menu button template
    frame_template_menu: function()
    {
        return  '<div class="galaxy-frame-scroll-up galaxy-frame-menu fa-icon-chevron-up fa-icon-2x"></div>' +
                '<div class="galaxy-frame-scroll-down galaxy-frame-menu fa-icon-chevron-down fa-icon-2x"></div>';
    }
});

// return
return {
    GalaxyFrameManager: GalaxyFrameManager
};

});
