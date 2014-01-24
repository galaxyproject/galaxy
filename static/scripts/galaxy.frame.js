/*
    galaxy frames
*/

// dependencies
define(["galaxy.masthead"], function(mod_masthead) {

// frame manager
var GalaxyFrame = Backbone.View.extend(
{
    // base element
    el_main: 'body',
    
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
        frame_max: 9
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
    visible: false,
    
    // frame active/disabled
    active: false,
    
    // button active
    button_active: null,
    
    // button load
    button_load  : null,
    
    // initialize
    initialize : function(options)
    {
        // add to masthead menu
        var self = this;
        
        // add activate icon
        this.button_active = new mod_masthead.GalaxyMastheadIcon (
        {
            icon        : 'fa-th',
            tooltip     : 'Enable/Disable Scratchbook',
            onclick     : function(e) { self._event_panel_active(e) },
            onunload    : function() {
                if (self.frame_counter > 0) {
                    return "You opened " + self.frame_counter + " frame(s) which will be lost.";
                }
            }
        });
        
        // add to masthead
        Galaxy.masthead.append(this.button_active);

        // add load icon
        this.button_load = new mod_masthead.GalaxyMastheadIcon (
        {
            icon        : 'fa-eye',
            tooltip     : 'Show/Hide Scratchbook',
            onclick     : function(e) { self._event_panel_load(e) },
            with_number : true
        });

        // add to masthead
        Galaxy.masthead.append(this.button_load);
        
        // read in defaults
        if (options)
            this.options = _.defaults(options, this.options);
        
        // initialize top
        this.top = this.top_max = this.options.top_min;
        
        // create
        this.setElement(this._template());
        
        // load background
        $(this.el).append(this._template_background());
        
        // load menu buttons
        $(this.el).append(this._template_menu());
        
        // load to main frame
        $(this.el_main).append($(this.el));

        //
        // define shadow frame
        //
        var id_shadow = '#frame-shadow';

        // add shadow template
        $(this.el).append(this._template_shadow(id_shadow.substring(1)));

        // initialize frame
        this.frame_shadow = {
            id              : id_shadow,
            screen_location : {},
            grid_location   : {},
            grid_rank       : null,
            grid_lock       : false
        };
        
        // initialize size
        this._frame_resize(this.frame_shadow, {width: 0, height: 0});
        
        // add shadow to frame list
        this.frame_list[id_shadow] = this.frame_shadow;
        
        // initialize panel
        this._panel_refresh();
       
        // catch window resize event
        var self = this;
        $(window).resize(function ()
        {
            if (self.visible)
                self._panel_refresh();
        });
    },
    
    // adds and displays a new frame/window
    add: function(options)
    {
        // frame default options
        var frameOptions =
        {
            title: '',
            content: null,
            target: '',
            type: null
        }
        
        // read in defaults
        if (options)
            options = _.defaults(options, frameOptions);
        else
            options = frameOptions;
    
        // check for content
        if(!options.content)
            return;
        
        // open new tab
        if (options.target == '_blank')
        {
            window.open(options.content);
            return;
        }
        
        // reload entire window
        if (options.target == '_top' || options.target == '_parent' || options.target == '_self')
        {
            window.location = options.content;
            return;
        }
        
        // validate
        if (!this.active)
        {
            // fix url if main frame is unavailable
            var $galaxy_main = $(window.parent.document).find('#galaxy_main');
            if (options.target == 'galaxy_main' || options.target == 'center')
            {
                if ($galaxy_main.length == 0)
                {
                    var href = options.content;
                    if (href.indexOf('?') == -1)
                        href += '?';
                    else
                        href += '&';
                    href += 'use_panels=True';
                    window.location = href;
                } else {
                    $galaxy_main.attr('src', options.content);
                }
            } else
                window.location = options.content;
                
            // stop
            return;
        }

        // check for number of frames
        if (this.frame_counter >= this.options.frame_max)
        {
            alert("You have reached the maximum number of allowed frames (" + this.options.frame_max + ").");   
            return;
        }

        // generate frame identifier
        var frame_id = '#frame-' + (this.frame_counter_id++);

        // check if frame exists
        if ($(frame_id).length !== 0)
        {
            alert("This frame already exists. This page might contain multiple frame managers.");
            return;
        }
        
        // reset top
        this.top = this.options.top_min;

        // append
        $(this.el).append(this._template_frame(frame_id.substring(1), options.title, options.type, options.content));
        
        // construct a new frame
        var frame = {
            id              : frame_id,
            screen_location : {},
            grid_location   : {},
            grid_rank       : null,
            grid_lock       : false
        };
        
        // set dimensions
        options.width   = this._to_pixel_coord('width', this.options.frame.cols);
        options.height  = this._to_pixel_coord('height', this.options.frame.rows);
        
        // default z-index
        this.frame_z = parseInt($(frame.id).css('z-index'));
        
        // add to frame list
        this.frame_list[frame_id] = frame;

        // increase frame counter
        this.frame_counter++;

        // resize
        this._frame_resize(frame, {width: options.width, height: options.height});
       
        // place frame
        this._frame_insert(frame, {top: 0, left: 0}, true);
            
        // show frames if hidden
        if (!this.visible)
            this._panel_show_hide();
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
    events:
    {
        // global frame events
        'mousemove'                         : '_event_frame_mouse_move',
        'mouseup'                           : '_event_frame_mouse_up',
        'mouseleave'                        : '_event_frame_mouse_up',
        'mousewheel'                        : '_event_panel_scroll',
        'DOMMouseScroll'                    : '_event_panel_scroll',
                
        // events fixed to elements
        'mousedown .frame'                  : '_event_frame_mouse_down',
        'mousedown .frame-background'       : '_event_panel_load',
        'mousedown .frame-scroll-up'        : '_event_panel_scroll_up',
        'mousedown .frame-scroll-down'      : '_event_panel_scroll_down',
        'mousedown .f-close'                : '_event_frame_close',
        'mousedown .f-pin'                  : '_event_frame_lock'
    },

    // drag start
    _event_frame_mouse_down: function (e)
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
        this.event.target = this._frame_identify(e.target);
       
        // check if frame is locked
        if (this.event.target.grid_lock)
        {
            this.event.type = null;
            return;
        }
        
        // backup event details
        this.event.xy = {x: e.originalEvent.pageX, y: e.originalEvent.pageY};
            
        // prepare drag/resize
        this._frame_drag_start(this.event.target);
    },

    // mouse move event
    _event_frame_mouse_move: function (e)
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
        var p = this._frame_screen (this.event.target);
        
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
            this._frame_resize(this.event.target, p);
            
            // break down to grid coordinates
            p.width = this._to_grid_coord('width', p.width) + 1;
            p.height = this._to_grid_coord('height', p.height) + 1;
            
            // transfer back to pixels
            p.width = this._to_pixel_coord('width', p.width);
            p.height = this._to_pixel_coord('height', p.height);
        
            // apply
            this._frame_resize(this.frame_shadow, p);
        
            // fix position
            this._frame_insert(this.frame_shadow, {
                top     : this._to_grid_coord('top', p.top),
                left    : this._to_grid_coord('left', p.left)
            });
        }
                 
        // drag event
        if (this.event.type == 'drag')
        {
            // update
            p.left  += event_xy_delta.x;
            p.top   += event_xy_delta.y;
            
            // apply
            this._frame_offset(this.event.target, p);

            // get location of shadow
            var l = {
                top     : this._to_grid_coord('top', p.top),
                left    : this._to_grid_coord('left', p.left)
            };
       
            // increase priority of current frame
            if (l.left !== 0)
                l.left++;
            
            // fix position
            this._frame_insert(this.frame_shadow, l);
        }
    },
    
    // mouse up
    _event_frame_mouse_up: function (e)
    {
        // check
        if (this.event.type != 'drag' && this.event.type != 'resize')
            return;
            
        // stop
        this._frame_drag_stop(this.event.target);
        
        // reset event
        this.event.type = null;
    },
    
    // drag start
    _event_frame_close: function (e)
    {
        // check
        if (this.event.type !== null)
            return;
        
        // prevent
        e.preventDefault();

        // get frame
        var frame = this._frame_identify(e.target);
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
            self._panel_refresh(true);
            
            // refresh scroll state once all animations completed
            self._panel_animation_complete();
            
            // hide if no frames left
            if (self.visible && self.frame_counter == 0)
                self._panel_show_hide();
        });
    },
    
    // drag start
    _event_frame_lock: function (e)
    {
        // check
        if (this.event.type !== null)
            return;
        
        // prevent
        e.preventDefault();

        // get frame
        var frame = this._frame_identify(e.target);
        
        // check
        if (frame.grid_lock)
        {
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
    _event_panel_load: function (e)
    {
        // check
        if (this.event.type !== null)
            return;

        // load panel
        this._panel_show_hide();
    },
    
    // activate/disable panel
    _event_panel_active: function (e)
    {
        // check
        if (this.event.type !== null)
            return;

        // load panel
        this._panel_active_disable();
    },
    
    // scroll
    _event_panel_scroll: function(e)
    {
        // check
        if (this.event.type !== null || !this.visible)
            return;
            
        // prevent
        e.preventDefault();

        // get wheel delta
        var delta = e.originalEvent.detail ? e.originalEvent.detail : e.originalEvent.wheelDelta / -3;
        
        // refresh panel
        this._panel_scroll(delta);
    },
    
    // scroll up
    _event_panel_scroll_up: function(e)
    {
        // check
        if (this.event.type !== null)
            return;
  
        // prevent
        e.preventDefault();

        // scroll up
        this._panel_scroll(-this.options.scroll);
    },
    
    // scroll down
    _event_panel_scroll_down: function(e)
    {
        // check
        if (this.event.type !== null)
            return;
     
        // prevent
        e.preventDefault();
        
        // scroll down
        this._panel_scroll(this.options.scroll);
    },
    
    /*
        FRAME EVENTS SUPPORT
    */
    
    // identify
    _frame_identify: function(target)
    {
        return this.frame_list['#' + $(target).closest('.frame').attr('id')];
    },

    // drag start
    _frame_drag_start : function (frame)
    {
        // set focus
        this._frame_focus(frame, true);
            
        // get current dimensions
        var p = this._frame_screen (frame);
        
        // initialize shadow
        this._frame_resize(this.frame_shadow, p);
        this._frame_grid(this.frame_shadow, frame.grid_location);
        
        // reset location
        frame.grid_location = null;
        
        // show shadow
        $(this.frame_shadow.id).show();
        
        // load frame cover
        $('.f-cover').show();
    },
    
    // drag stop
    _frame_drag_stop : function (frame)
    {
        // remove focus
        this._frame_focus(frame, false);
        
        // get new dimensions
        var p = this._frame_screen(this.frame_shadow);
        
        // update frame
        this._frame_resize(frame, p);
        this._frame_grid(frame, this.frame_shadow.grid_location, true);
        
        // reset location of shadow
        this.frame_shadow.grid_location = null;

        // hide shadow
        $(this.frame_shadow.id).hide();
        
        // hide frame cover
        $('.f-cover').hide();
        
        // refresh scroll state once all animations completed
        this._panel_animation_complete();
    },
    
    /*
        GRID/PIXEL CONVERTER
    */
    
    // converts a pixel coordinate to grids
    _to_grid_coord: function (type, px)
    {
        // determine sign
        var sign = (type == 'width' || type == 'height') ? 1 : -1;
        
        if (type == 'top') px -= this.top;
        
        // return
        return parseInt((px + sign * this.options.margin) / this.options.cell, 10);
    },
    
    // converts a grid coordinate to pixels
    _to_pixel_coord: function (type, g)
    {
        // determine sign
        var sign = (type == 'width' || type == 'height') ? 1 : -1;
        
        // return
        var px = (g * this.options.cell) - sign * this.options.margin;
        
        if (type == 'top') px += this.top;
        
        return px;
    },
    
    // get grid coordinates
    _to_grid: function (px)
    {
        // full set
        return {
            top     : this._to_grid_coord('top', px.top),
            left    : this._to_grid_coord('left', px.left),
            width   : this._to_grid_coord('width', px.width),
            height  : this._to_grid_coord('height', px.height)
        };
    },
       
    // get pixel coordinates
    _to_pixel: function(g)
    {
        return {
            top     : this._to_pixel_coord('top', g.top),
            left    : this._to_pixel_coord('left', g.left),
            width   : this._to_pixel_coord('width', g.width),
            height  : this._to_pixel_coord('height', g.height)
        };
    },

    /* 
        COLLISION DETECTION
    */
    
    // check collision
    _is_collision: function(g)
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
    _location_rank: function(loc)
    {
        return (loc.top * this.cols) + loc.left;
    },
    
    /*
        ONSCREEN MENU
    */
    
    // update frame counter
    _menu_refresh: function()
    {
        // update on screen counter
        this.button_load.number(this.frame_counter);
        
        // check
        if(this.frame_counter == 0)
            this.button_load.hide();
        else
            this.button_load.show();
            
        // scroll up possible?
        if (this.top == this.options.top_min)
            $(".frame-scroll-up").hide();
        else
            $(".frame-scroll-up").show();
        
        // scroll down possible?
        if (this.top == this.top_max)
            $(".frame-scroll-down").hide();
        else
            $(".frame-scroll-down").show();
    },
    
    /*
        PANEL/WINDOW FUNCTIONS
    */

    // panel on animation complete / frames not moving
    _panel_animation_complete: function()
    {
        var self = this;
        $(".frame").promise().done(function() {self._panel_scroll(0, true)});
    },

    // refresh panel
    _panel_refresh: function(animate)
    {
        // get current size
        this.cols = parseInt($(window).width() / this.options.cell, 10) + 1;
        
        // recalculate frame positions
        this._frame_insert(null, null, animate);
    },
    
    // update scroll
    _panel_scroll: function(delta, animate)
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
                    this._frame_offset(frame, screen_location, animate);
                }
            }
            
            // update top value
            this.top = top_new;
        }
        
        // refresh
        this._menu_refresh();
    },
    
    // show or hide panel
    _panel_show_hide: function()
    {           
        // check
        if (this.visible)
        {
            // hide
            this.visible = false;
            
            // hide 
            $(".frame").fadeOut('fast');
            
            // add class
            this.button_load.icon("fa-eye-slash");
            this.button_load.untoggle();
            
            // hide background
            $(".frame-background").hide();
            
            // hide menu
            $(".frame-menu").hide();
        } else {
            // show
            this.visible = true;
            
            // show
            $(".frame").fadeIn('fast');
            
            // add class
            this.button_load.icon("fa-eye");
            this.button_load.toggle();
            
            // hide shadow
            $(this.frame_shadow.id).hide();
        
            // show background
            $(".frame-background").show();
            
            // show panel
            this._panel_refresh();
        }
    },
    
    // show or hide panel
    _panel_active_disable: function()
    {
        // check
        if (this.active)
        {
            // disable
            this.active = false;

            // toggle
            this.button_active.untoggle();
    
            // hide panel
            if (this.visible)
                this._panel_show_hide();
        } else {
            // activate
            this.active = true;
        
            // untoggle
            this.button_active.toggle();
        }
    },
    
    /*
        FRAME FUNCTIONS
    */
      
    // frame insert at given location
    _frame_insert: function(frame, new_loc, animate)
    {
        // define
        var place_list = [];
       
        // frame to place
        if (frame)
        {
            // reset grid location
            frame.grid_location = null;
            
            // set first one to be placed
            place_list.push([frame, this._location_rank(new_loc)]);
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
            this._frame_place(place_list[i][0], animate);
        
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
        this._menu_refresh();
    },

    // naive frame place
    _frame_place: function(frame, animate)
    {
        // reset grid location
        frame.grid_location = null;
        
        // grid coordinates of new frame
        var g = this._to_grid(this._frame_screen(frame));
        
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
                if (!this._is_collision(g))
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
            this._frame_grid(frame, g, animate);
        else
            console.log("Grid dimensions exceeded.");
    },
    
    // focus
    _frame_focus: function(frame, has_focus)
    {
        // get new z-value
        var z = this.frame_z + (has_focus ? 1 : 0);
        
        // update
        $(frame.id).css('z-index', z);
    },
    
    // new left/top position frame
    _frame_offset: function(frame, p, animate)
    {
        // update screen location
        frame.screen_location.left = p.left;
        frame.screen_location.top = p.top;
                
        // animate
        if (animate)
        {
            // set focus on animated
            this._frame_focus(frame, true);
            
            // prepare for callback
            var self = this;
            
            // animate and remove focus
            $(frame.id).animate({top: p.top, left: p.left}, 'fast', function()
            {
                // remove focus
                self._frame_focus(frame, false);
            });
        } else
            // update css
            $(frame.id).css({top: p.top, left: p.left});
    },

    // resize frame
    _frame_resize: function(frame, p)
    {
        // update css
        $(frame.id).css({width: p.width, height: p.height});
    
        // update descriptor
        frame.screen_location.width = p.width;
        frame.screen_location.height = p.height;
    },

    // new grid location
    _frame_grid: function (frame, l, animate)
    {
        // update grid location
        frame.grid_location = l;

        // place frame
        this._frame_offset(frame, this._to_pixel(l), animate);
            
        // update grid rank
        frame.grid_rank = this._location_rank(l);
    },
    
    // get frame dimensions
    _frame_screen: function(frame)
    {   
        var p = frame.screen_location;
        return {top: p.top, left: p.left, width: p.width, height: p.height};
    },
    
    /*
        HTML TEMPLATES
    */
    
    // main element
    _template: function()
    {
        return  '<div class="galaxy-frame"></div>';
    },
    
    // fill regular frame template
    _template_frame: function(id, title, type, content)
    {
        // check title
        if (!title)
            title = '';

        // identify content type
        if (type == 'url') {
            if (content.indexOf('?') == -1)
                content += '?';
            else
                content += '&';
            content += 'widget=True';
            content = '<iframe scrolling="auto" class="f-iframe" src="' + content + '"></iframe>';
        }
        
        // load template
        return  '<div id="' + id + '" class="frame corner">' +
                    '<div class="f-header corner">' +
                        '<span class="f-title">' + title + '</span>' +
                        '<span class="f-icon f-pin fa fa-thumb-tack"></span>' +
                        '<span class="f-icon f-close fa fa-trash-o"></span>' +
                    '</div>' +
                    '<div class="f-content">' + content +
                        '<div class="f-cover"></div>' +
                    '</div>' +
                    '<span class="f-resize f-icon corner fa fa-resize-full"></span>' +
                '</div>';
    },
    
    // fill shadow template
    _template_shadow: function(id)
    {
        return '<div id="' + id + '" class="frame-shadow corner"></div>';
    },
    
    // fill background template in order to cover underlying iframes
    _template_background: function()
    {
        return '<div class="frame-background"></div>';
    },
    
    // fill menu button template
    _template_menu: function()
    {
        return  '<div class="frame-scroll-up frame-menu fa fa-chevron-up fa-2x"></div>' +
                '<div class="frame-scroll-down frame-menu fa fa-chevron-down fa-2x"></div>';
    }
});

// return
return {
    GalaxyFrame: GalaxyFrame
};

});
