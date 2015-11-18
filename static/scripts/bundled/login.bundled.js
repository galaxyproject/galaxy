webpackJsonp([6],{

/***/ 0:
/*!**************************************!*\
  !*** ./galaxy/scripts/apps/login.js ***!
  \**************************************/
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function(_) {
	var jQuery = __webpack_require__( /*! jquery */ 3 ),
	    $ = jQuery,
	    PANEL = __webpack_require__( /*! layout/panel */ 5 ),
	    _l = __webpack_require__( /*! utils/localization */ 8 ),
	    PAGE = __webpack_require__( /*! layout/page */ 120 );
	
	window.app = function app( options, bootstrapped ){
	    console.debug( 'building app:', options, bootstrapped );
	
	    // TODO: remove iframe for user login (at least) and render login page from here
	    // then remove this redirect
	    if( !options.show_welcome_with_login ){
	        window.location.href = Galaxy.root + 'user/login?use_panels=True';
	        return;
	    }
	
	    var loginPage = new PAGE.PageLayoutView( _.extend( options, {
	        el      : 'body',
	        center  : new PANEL.CenterPanel({ el : '#center' }),
	        right   : new PANEL.RightPanel({
	            title : _l( 'Login required' ),
	            el : '#right'
	        }),
	    }));
	
	    $(function(){
	        // TODO: incorporate *actual* referrer/redirect info as the original page does
	        var loginUrl = Galaxy.root + 'user/login?redirect=' + encodeURI( Galaxy.root );
	        loginPage.render();
	
	        // welcome page (probably) needs to remain sandboxed
	        loginPage.center.$( '#galaxy_main' ).prop( 'src', options.welcome_url );
	
	        loginPage.right.$( '.unified-panel-body' )
	            .css( 'overflow', 'hidden' )
	            .html( '<iframe src="' + loginUrl + '" frameborder="0" style="width: 100%; height: 100%;"/>' );
	    });
	};
	
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(/*! underscore */ 1)))

/***/ },

/***/ 14:
/*!*******************************************!*\
  !*** ./galaxy/scripts/mvc/ui/ui-modal.js ***!
  \*******************************************/
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(Backbone, $, _) {!(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = function() {
	
	var View = Backbone.View.extend({
	
	    // base element
	    elMain: 'body',
	    
	    // defaults options
	    optionsDefault: {
	        title            : 'ui-modal',
	        body             : '',
	        backdrop         : true,
	        height           : null,
	        width            : null,
	        closing_events   : false,
	        closing_callback : null,
	        title_separator  : true
	    },
	
	    // button list
	    buttonList: {},
	
	    // initialize
	    initialize : function(options) {
	        if (options){
	            this._create(options);
	        }
	    },
	    
	    // adds and displays a new frame/window
	    show: function(options) {
	        // create
	        this.initialize(options);
	        
	        // fix height
	        if (this.options.height){
	            this.$body.css('height', this.options.height);
	            this.$body.css('overflow', 'hidden');
	        } else {
	            this.$body.css('max-height', $(window).height() / 2);
	        }
	
	        // fix width
	        if (this.options.width) {
	            this.$dialog.css('width', this.options.width);
	        }
	
	        // show
	        if (this.visible) {
	            this.$el.show();
	        } else {
	            this.$el.fadeIn('fast');
	        }
	
	        // set visible flag
	        this.visible = true;
	    },
	
	    // hide
	    hide: function() {
	        this.visible = false;
	        this.$el.fadeOut('fast');
	        if (this.options.closing_callback){
	            this.options.closing_callback();
	        }
	    },
	
	    // enable buttons
	    enableButton: function(name) {
	        var button_id = this.buttonList[name];
	        this.$buttons.find('#' + button_id).prop('disabled', false);
	    },
	
	    // disable buttons
	    disableButton: function(name) {
	        var button_id = this.buttonList[name];
	        this.$buttons.find('#' + button_id).prop('disabled', true);
	    },
	    
	    // show buttons
	    showButton: function(name) {
	        var button_id = this.buttonList[name];
	        this.$buttons.find('#' + button_id).show();
	    },
	
	    // hide buttons
	    hideButton: function(name) {
	        var button_id = this.buttonList[name];
	        this.$buttons.find('#' + button_id).hide();
	    },
	    
	    // get button
	    getButton: function(name) {
	        var button_id = this.buttonList[name];
	        return this.$buttons.find('#' + button_id);
	    },
	    
	    // returns scroll top for body element
	    scrollTop: function() {
	        return this.$body.scrollTop();
	    },
	
	    // create
	    _create: function(options) {
	        // link this
	        var self = this;
	        
	        // configure options
	        this.options = _.defaults(options, this.optionsDefault);
	        
	        // check for progress bar request
	        if (this.options.body == 'progress'){
	            this.options.body = $('<div class="progress progress-striped active"><div class="progress-bar progress-bar-info" style="width:100%"></div></div>');
	        }
	            
	        // remove former element
	        if (this.$el) {
	            // remove element
	            this.$el.remove();
	            
	            // remove escape event
	            $(document).off('keyup.ui-modal');
	        }
	        
	        // create new element
	        this.setElement(this._template(this.options.title));
	        
	        // link elements
	        this.$dialog = (this.$el).find('.modal-dialog');
	        this.$body = (this.$el).find('.modal-body');
	        this.$footer  = (this.$el).find('.modal-footer');
	        this.$buttons = (this.$el).find('.buttons');
	        this.$backdrop = (this.$el).find('.modal-backdrop');
	        
	        // append body
	        this.$body.html(this.options.body);
	        
	        // configure background
	        if (!this.options.backdrop){
	            this.$backdrop.removeClass('in');
	        }
	                        
	        // append buttons
	        if (this.options.buttons) {
	            // reset button list
	            this.buttonList = {};
	            var counter = 0;
	            $.each(this.options.buttons, function(name, value) {
	                var button_id = 'button-' + counter++;
	                self.$buttons.append($('<button id="' + button_id + '"></button>').text(name).click(value)).append(" ");
	                self.buttonList[name] = button_id;
	            });
	        } else {
	            // hide footer
	            this.$footer.hide();
	        }
	        
	        // append to main element
	        $(this.elMain).append($(this.el));
	
	        // bind additional closing events
	        if (this.options.closing_events) {
	            // bind the ESC key to hide() function
	            $(document).on('keyup.ui-modal', function(e) {
	                if (e.keyCode == 27) {
	                    self.hide();
	                }
	            });
	            
	            // hide modal if background is clicked
	            this.$el.find('.modal-backdrop').on('click', function() { self.hide(); });
	        }
	
	        // removes the default separator line
	        if (!this.options.title_separator) {
	            this.$('.modal-header').css({ 'border': 'none', 'padding-bottom': '0px' });
	        }
	    },
	    
	    // fill regular modal template
	    _template: function(title) {
	        return  '<div class="ui-modal modal">' +
	                    '<div class="modal-backdrop fade in" style="z-index: -1;"></div>' +
	                    '<div class="modal-dialog">' +
	                        '<div class="modal-content">' +
	                            '<div class="modal-header">' +
	                                '<button type="button" class="close" style="display: none;">&times;</button>' +
	                                '<h4 class="title">' + title + '</h4>' +
	                            '</div>' +
	                            '<div class="modal-body" style="position: static;"></div>' +
	                            '<div class="modal-footer">' +
	                                '<div class="buttons" style="float: right;"></div>' +
	                            '</div>' +
	                        '</div' +
	                    '</div>' +
	                '</div>';
	    }
	});
	
	return {
	    View : View
	}
	
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(/*! libs/backbone */ 2), __webpack_require__(/*! jquery */ 3), __webpack_require__(/*! underscore */ 1)))

/***/ },

/***/ 15:
/*!********************************************!*\
  !*** ./galaxy/scripts/mvc/ui/ui-frames.js ***!
  \********************************************/
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(Backbone, _, $) {// dependencies
	!(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = function() {
	
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
	        };
	
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
	        var sign = (type == 'width' || type == 'height') ? 1 : -1;
	        if (type == 'top') px -= this.top;
	        return parseInt((px + sign * this.options.margin) / this.options.cell, 10);
	    },
	    
	    // converts a grid coordinate to pixels
	    _toPixelCoord: function (type, g) {
	        var sign = (type == 'width' || type == 'height') ? 1 : -1;
	        var px = (g * this.options.cell) - sign * this.options.margin;
	        if (type == 'top') px += this.top;
	        return px;
	    },
	
	    // get grid coordinates
	    _toGrid: function (px) {
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
	            $(frame.id).animate({top: p.top, left: p.left}, 'fast', function() {
	                self._frameFocus(frame, false);
	            });
	        } else {
	            $(frame.id).css({top: p.top, left: p.left});
	        }
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
	                    '<span class="f-resize f-icon corner fa fa-expand"></span>' +
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
	
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(/*! libs/backbone */ 2), __webpack_require__(/*! underscore */ 1), __webpack_require__(/*! jquery */ 3)))

/***/ },

/***/ 18:
/*!***************************************!*\
  !*** ./galaxy/scripts/utils/utils.js ***!
  \***************************************/
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function($, jQuery, _) {/**
	 * Galaxy utilities comprises small functions, which at this point
	 * do not require their own classes/files
	*/
	
	// dependencies
	!(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = function() {
	
	/** Traverse through json
	*/
	function deepeach(dict, callback) {
	    for (var i in dict) {
	        var d = dict[i];
	        if (d && typeof(d) == "object") {
	            callback(d);
	            deepeach(d, callback);
	        }
	    }
	}
	
	/**
	 * Check if a string is a json string
	 * @param{String}   text - Content to be validated
	 */
	function isJSON(text) {
	    return /^[\],:{}\s]*$/.test(text.replace(/\\["\\\/bfnrtu]/g, '@').
	        replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g, ']').
	        replace(/(?:^|:|,)(?:\s*\[)+/g, ''));
	};
	
	/**
	 * Sanitize/escape a string
	 * @param{String}   content - Content to be sanitized
	 */
	function sanitize(content) {
	    return $('<div/>').text(content).html();
	};
	
	/**
	 * Validate atomic values or list of values
	 * usually used for selectable options
	 * @param{String}   value - Value or list to be validated
	 */
	function validate (value) {
	    if (!(value instanceof Array)) {
	        value = [value];
	    }
	    if (value.length === 0) {
	        return false;
	    }
	    for (var i in value) {
	        if (['__null__', '__undefined__', null, undefined].indexOf(value[i]) > -1) {
	            return false;
	        }
	    }
	    return true;
	};
	
	/**
	 * Convert list to pretty string
	 * @param{String}   lst - List of strings to be converted in human readable list sentence
	 */
	function textify(lst) {
	    var lst = lst.toString();
	    if (lst) {
	        lst = lst.replace(/,/g, ', ');
	        var pos = lst.lastIndexOf(', ');
	        if (pos != -1) {
	            lst = lst.substr(0, pos) + ' or ' + lst.substr(pos+1);
	        }
	        return lst;
	    }
	    return '';
	};
	
	/**
	 * Request handler for GET
	 * @param{String}   url     - Url request is made to
	 * @param{Function} success - Callback on success
	 * @param{Function} error   - Callback on error
	 * @param{Boolean}  cache   - Use cached data if available
	 */
	function get (options) {
	    top.__utils__get__ = top.__utils__get__ || {};
	    if (options.cache && top.__utils__get__[options.url]) {
	        options.success && options.success(top.__utils__get__[options.url]);
	        console.debug('utils.js::get() - Fetching from cache [' + options.url + '].');
	    } else {
	        request({
	            url     : options.url,
	            data    : options.data,
	            success : function(response) {
	                top.__utils__get__[options.url] = response;
	                options.success && options.success(response);
	            },
	            error : function(response) {
	                options.error && options.error(response);
	            }
	        });
	    }
	};
	
	/**
	 * Request handler
	 * @param{String}   method  - Request method ['GET', 'POST', 'DELETE', 'PUT']
	 * @param{String}   url     - Url request is made to
	 * @param{Object}   data    - Data send to url
	 * @param{Function} success - Callback on success
	 * @param{Function} error   - Callback on error
	 */
	function request (options) {
	    // prepare ajax
	    var ajaxConfig = {
	        contentType : 'application/json',
	        type        : options.type || 'GET',
	        data        : options.data || {},
	        url         : options.url
	    }
	
	    // encode data into url
	    if (ajaxConfig.type == 'GET' || ajaxConfig.type == 'DELETE') {
	        if (ajaxConfig.url.indexOf('?') == -1) {
	            ajaxConfig.url += '?';
	        } else {
	            ajaxConfig.url += '&';
	        }
	        ajaxConfig.url      = ajaxConfig.url + $.param(ajaxConfig.data, true);
	        ajaxConfig.data     = null;
	    } else {
	        ajaxConfig.dataType = 'json';
	        ajaxConfig.url      = ajaxConfig.url;
	        ajaxConfig.data     = JSON.stringify(ajaxConfig.data);
	    }
	
	    // make request
	    $.ajax(ajaxConfig)
	    .done(function(response) {
	        if (typeof response === 'string') {
	            try {
	                response = response.replace('Infinity,', '"Infinity",');
	                response = jQuery.parseJSON(response);
	            } catch (e) {
	                console.debug(e);
	            }
	        }
	        options.success && options.success(response);
	    })
	    .fail(function(response) {
	        var response_text = null;
	        try {
	            response_text = jQuery.parseJSON(response.responseText);
	        } catch (e) {
	            response_text = response.responseText;
	        }
	        options.error && options.error(response_text, response);
	    });
	};
	
	/**
	 * Read a property value from CSS
	 * @param{String}   classname   - CSS class
	 * @param{String}   name        - CSS property
	 */
	function cssGetAttribute (classname, name) {
	    var el = $('<div class="' + classname + '"></div>');
	    el.appendTo(':eq(0)');
	    var value = el.css(name);
	    el.remove();
	    return value;
	};
	
	/**
	 * Load a CSS file
	 * @param{String}   url - Url of CSS file
	 */
	function cssLoadFile (url) {
	    if (!$('link[href^="' + url + '"]').length) {
	        $('<link href="' + Galaxy.root + url + '" rel="stylesheet">').appendTo('head');
	    }
	};
	
	/**
	 * Safely merge to dictionaries
	 * @param{Object}   options         - Target dictionary
	 * @param{Object}   optionsDefault  - Source dictionary
	 */
	function merge (options, optionsDefault) {
	    if (options) {
	        return _.defaults(options, optionsDefault);
	    } else {
	        return optionsDefault;
	    }
	};
	
	
	/**
	 * Round floaing point 'number' to 'numPlaces' number of decimal places.
	 * @param{Object}   number      a floaing point number
	 * @param{Object}   numPlaces   number of decimal places
	 */
	function roundToDecimalPlaces( number, numPlaces ){
	    var placesMultiplier = 1;
	    for( var i=0; i<numPlaces; i++ ){
	        placesMultiplier *= 10;
	    }
	    return Math.round( number * placesMultiplier ) / placesMultiplier;
	}
	
	// calculate on import
	var kb = 1024,
	    mb = kb * kb,
	    gb = mb * kb,
	    tb = gb * kb;
	/**
	 * Format byte size to string with units
	 * @param{Integer}   size           - Size in bytes
	 * @param{Boolean}   normal_font    - Switches font between normal and bold
	 */
	function bytesToString (size, normal_font, numberPlaces) {
	    numberPlaces = numberPlaces !== undefined? numberPlaces: 1;
	    // identify unit
	    var unit = "";
	    if (size >= tb){ size = size / tb; unit = 'TB'; } else
	    if (size >= gb){ size = size / gb; unit = 'GB'; } else
	    if (size >= mb){ size = size / mb; unit = 'MB'; } else
	    if (size >= kb){ size = size / kb; unit = 'KB'; } else
	    if (size >  0){ unit = 'b'; }
	    else { return normal_font? '0 b': '<strong>-</strong>'; }
	    // return formatted string
	    var rounded = unit == 'b'? size: roundToDecimalPlaces( size, numberPlaces );
	    if (normal_font) {
	       return  rounded + ' ' + unit;
	    } else {
	        return '<strong>' + rounded + '</strong> ' + unit;
	    }
	};
	
	/**
	 * Create a unique id
	 */
	function uid(){
	    top.__utils__uid__ = top.__utils__uid__ || 0;
	    return 'uid-' + top.__utils__uid__++;
	};
	
	/**
	 * Create a time stamp
	 */
	function time() {
	    var d = new Date();
	    var hours = (d.getHours() < 10 ? "0" : "") + d.getHours();
	    var minutes = (d.getMinutes() < 10 ? "0" : "") + d.getMinutes()
	    return datetime = d.getDate() + "/"
	                + (d.getMonth() + 1)  + "/"
	                + d.getFullYear() + ", "
	                + hours + ":"
	                + minutes;
	};
	
	return {
	    cssLoadFile: cssLoadFile,
	    cssGetAttribute: cssGetAttribute,
	    get: get,
	    merge: merge,
	    bytesToString: bytesToString,
	    uid: uid,
	    time: time,
	    request: request,
	    sanitize: sanitize,
	    textify: textify,
	    validate: validate,
	    deepeach: deepeach,
	    isJSON: isJSON
	};
	
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(/*! jquery */ 3), __webpack_require__(/*! jquery */ 3), __webpack_require__(/*! underscore */ 1)))

/***/ },

/***/ 120:
/*!***************************************!*\
  !*** ./galaxy/scripts/layout/page.js ***!
  \***************************************/
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(Backbone, _, $) {!(__WEBPACK_AMD_DEFINE_ARRAY__ = [
	    __webpack_require__(/*! layout/masthead */ 121),
	    __webpack_require__(/*! layout/panel */ 5),
	    __webpack_require__(/*! mvc/ui/ui-modal */ 14),
	    __webpack_require__(/*! mvc/base-mvc */ 6)
	], __WEBPACK_AMD_DEFINE_RESULT__ = function( MASTHEAD, PANEL, MODAL, BASE_MVC ) {
	
	// ============================================================================
	var PageLayoutView = Backbone.View.extend( BASE_MVC.LoggableMixin ).extend({
	    _logNamespace : 'layout',
	
	    el : 'body',
	    className : 'full-content',
	
	    _panelIds : [
	        'left', 'center', 'right'
	    ],
	
	    defaultOptions : {
	        message_box_visible : false,
	        message_box_content : '',
	        message_box_class   : 'info',
	
	        show_inactivity_warning : false,
	        inactivity_box_content  : '',
	    },
	
	    initialize : function( options ){
	        this.log( this + '.initialize:', options );
	        _.extend( this, _.pick( options, this._panelIds ) );
	        this.options = _.defaults( _.omit( options, this._panelIds ), this.defaultOptions );
	
	        // TODO: remove globals
	        Galaxy.modal = this.modal = new MODAL.View();
	    },
	
	    /**  */
	    $everything : function(){
	        return this.$( '#everything' );
	    },
	
	    render : function(){
	        this.log( this + '.render:' );
	        this.$el.attr( 'scroll', 'no' );
	        this.$el.html( this.template( this.options ) );
	
	        //TODO: no render on masthead, needs init each time
	        Galaxy.masthead = this.masthead = new MASTHEAD.GalaxyMasthead( _.extend( this.options.config, {
	            el: this.$( '#masthead' ).get(0)
	        }));
	
	        if( this.options.message_box_visible ){
	            this.messageBox( this.options.message_box_content, this.options.message_box_class );
	        }
	        if( this.options.show_inactivity_warning ){
	            this.inactivityWarning( this.options.inactivity_box_content );
	        }
	
	        this.renderPanels();
	        return this;
	    },
	
	    /**  */
	    messageBox : function( content, level ){
	        content = content || '';
	        level = level || 'info';
	        this.$el.addClass( 'has-message-box' );
	        this.$( '#messagebox' )
	            .attr( 'class', 'panel-' + level + '-message' )
	            .html( content )
	            .toggle( !!content );
	        return this;
	    },
	
	    /**  */
	    inactivityWarning : function( content ){
	        var verificationLink = '<a href="' + Galaxy.root + 'user/resend_verification">Resend verification.</a>';
	        this.$el.addClass( 'has-inactivity-box' );
	        this.$( '#inactivebox' )
	            .html( content )
	            .append( ' ' + verificationLink )
	            .toggle( !!content );
	        return this;
	    },
	
	    /**  */
	    renderPanels : function(){
	        var page = this;
	        // TODO: Remove this line after select2 update
	        $( '.select2-hidden-accessible' ).remove();
	        this._panelIds.forEach( function( panelId ){
	            if( _.has( page, panelId ) ){
	                var panelView = page[ panelId ];
	                panelView.setElement( '#' + panelId );
	                panelView.render();
	            }
	        });
	        if( !this.left ){
	            this.center.$el.css( 'left', 0 );
	        }
	        if( !this.right ){
	            this.center.$el.css( 'right', 0 );
	        }
	        return this;
	    },
	
	    /** body template */
	    //TODO: to underscore
	    template: function( options ){
	        //TODO: remove inline styling
	        return [
	            '<div id="everything" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">',
	                '<div id="background"/>',
	                '<div id="masthead" class="navbar navbar-fixed-top navbar-inverse"></div>',
	                '<div id="messagebox" style="display: none;"></div>',
	                '<div id="inactivebox" class="panel-warning-message" style="display: none;"></div>',
	                // content here
	                // TODO: wrapping div
	                this.left?   '<div id="left"/>' : '',
	                this.center? '<div id="center" class="inbound"/>' : '',
	                this.right?  '<div id="right"/>' : '',
	            '</div>',
	            // a dropdown overlay for capturing clicks/drags
	            '<div id="dd-helper" style="display: none;"></div>',
	            // display message when js is disabled
	            '<noscript>',
	                '<div class="overlay overlay-background noscript-overlay">',
	                    '<div>',
	                        '<h3 class="title">Javascript Required for Galaxy</h3>',
	                        '<div>',
	                            'The Galaxy analysis interface requires a browser with Javascript enabled.<br>',
	                            'Please enable Javascript and refresh this page',
	                        '</div>',
	                    '</div>',
	                '</div>',
	            '</noscript>'
	        ].join('');
	    },
	
	    hideSidePanels : function(){
	        if( this.left ){
	            this.left.hide();
	        }
	        if( this.right ){
	            this.right.hide();
	        }
	    },
	
	    toString : function(){ return 'PageLayoutView'; }
	});
	
	// ============================================================================
	    return {
	        PageLayoutView: PageLayoutView
	    };
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(/*! libs/backbone */ 2), __webpack_require__(/*! underscore */ 1), __webpack_require__(/*! jquery */ 3)))

/***/ },

/***/ 121:
/*!*******************************************!*\
  !*** ./galaxy/scripts/layout/masthead.js ***!
  \*******************************************/
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(Backbone, $) {!(__WEBPACK_AMD_DEFINE_ARRAY__ = [
	    __webpack_require__(/*! utils/utils */ 18),
	    __webpack_require__(/*! layout/menu */ 122),
	    __webpack_require__(/*! layout/scratchbook */ 123),
	    __webpack_require__(/*! mvc/user/user-quotameter */ 140),
	], __WEBPACK_AMD_DEFINE_RESULT__ = function(Utils, Menu, Scratchbook, QuotaMeter) {
	
	/** Masthead **/
	var GalaxyMasthead = Backbone.View.extend({
	    // base element
	    el_masthead: '#everything',
	
	    // options
	    options : null,
	
	    // background
	    $background: null,
	
	    // list
	    list: [],
	
	    // initialize
	    initialize : function(options) {
	        // update options
	        this.options = options;
	
	        // HACK: due to body events defined in panel.js
	        $("body").off();
	
	        // define this element
	        this.setElement($(this._template(options)));
	        // add to page
	        $( '#masthead' ).replaceWith( this.$el );
	
	        // assign background
	        this.$background = $(this.el).find('#masthead-background');
	
	        // loop through unload functions if the user attempts to unload the page
	        var self = this;
	        $(window).on('beforeunload', function() {
	            var text = "";
	            for (var key in self.list) {
	                if (self.list[key].options.onunload) {
	                    var q = self.list[key].options.onunload();
	                    if (q) text += q + " ";
	                }
	            }
	            if (text !== "") {
	                return text;
	            }
	        });
	
	        // construct default menu options
	        this.menu = Galaxy.menu = new Menu.GalaxyMenu({
	            masthead    : this,
	            config      : this.options
	        });
	
	        // scratchpad
	        this.frame = Galaxy.frame = new Scratchbook.GalaxyFrame({
	            masthead    : this,
	        });
	
	        // set up the quota meter (And fetch the current user data from trans)
	        // add quota meter to masthead
	        Galaxy.quotaMeter = new QuotaMeter.UserQuotaMeter({
	            model       : Galaxy.user,
	            el          : this.$( '.quota-meter-container' )
	        }).render();
	    },
	
	    // configure events
	    events: {
	        'click'     : '_click',
	        'mousedown' : function(e) { e.preventDefault() }
	    },
	
	    // adds a new item to the masthead
	    append : function(item) {
	        return this._add(item, true);
	    },
	
	    // adds a new item to the masthead
	    prepend : function(item) {
	        return this._add(item, false);
	    },
	
	    // activate
	    highlight: function(id) {
	        var current = $(this.el).find('#' + id + '> li');
	        if (current) {
	            current.addClass('active');
	        }
	    },
	
	    // adds a new item to the masthead
	    _add : function(item, append) {
	        var $loc = $(this.el).find('#' + item.location);
	        if ($loc){
	            // create frame for new item
	            var $current = $(item.el);
	
	            // configure class in order to mark new items
	            $current.addClass('masthead-item');
	
	            // append to masthead
	            if (append) {
	                $loc.append($current);
	            } else {
	                $loc.prepend($current);
	            }
	
	            // add to list
	            this.list.push(item);
	        }
	
	        // location not found
	        return null;
	    },
	
	    // handle click event
	    _click: function(e) {
	        // close all popups
	        var $all = $(this.el).find('.popup');
	        if ($all) {
	            $all.hide();
	        }
	
	        // open current item
	        var $current = $(e.target).closest('.masthead-item').find('.popup');
	        if ($(e.target).hasClass('head')) {
	            $current.show();
	            this.$background.show();
	        } else {
	            this.$background.hide();
	        }
	    },
	
	    /*
	        HTML TEMPLATES
	    */
	
	    // fill template
	    _template: function(options) {
	        var brand_text = options.brand ? ("/ " + options.brand) : "" ;
	        return  '<div><div id="masthead" class="navbar navbar-fixed-top navbar-inverse">' +
	                    '<div style="position: relative; right: -50%; float: left;">' +
	                        '<div id="navbar" style="display: block; position: relative; right: 50%;"></div>' +
	                    '</div>' +
	                   '<div class="navbar-brand">' +
	                        '<a href="' + options.logo_url + '">' +
	                            '<img style="margin-left: 0.35em;" border="0" src="' + Galaxy.root + 'static/images/galaxyIcon_noText.png">' +
	                            '<span id="brand"> Galaxy ' + brand_text + '</span>' +
	                        '</a>' +
	                    '</div>' +
	                    '<div class="quota-meter-container"></div>' +
	                    '<div id="iconbar" class="iconbar"></div>' +
	                '</div>' +
	                '<div id="masthead-background" style="display: none; position: absolute; top: 33px; width: 100%; height: 100%; z-index: 1010"></div>' +
	                '</div>';
	    }
	});
	
	// return
	return {
	    GalaxyMasthead: GalaxyMasthead
	};
	
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(/*! libs/backbone */ 2), __webpack_require__(/*! jquery */ 3)))

/***/ },

/***/ 122:
/*!***************************************!*\
  !*** ./galaxy/scripts/layout/menu.js ***!
  \***************************************/
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(Backbone, _, $) {// dependencies
	!(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = function() {
	
	/** GalaxyMenu uses the GalaxyMasthead class in order to add menu items and icons to the Masthead **/
	var GalaxyMenu = Backbone.Model.extend({
	    initialize: function( options ) {
	        this.options = options.config;
	        this.masthead  = options.masthead;
	        this.create();
	    },
	
	    // default menu
	    create: function() {
	        //
	        // Analyze data tab.
	        //
	        var tab_analysis = new GalaxyMastheadTab({
	            id              : 'analysis',
	            title           : 'Analyze Data',
	            content         : '',
	            title_attribute : 'Analysis home view'
	        });
	        this.masthead.append( tab_analysis );
	
	        //
	        // Workflow tab.
	        //
	
	        var workflow_options = {
	            id              : 'workflow',
	            title           : 'Workflow',
	            content         : 'workflow',
	            title_attribute : 'Chain tools into workflows'
	        }
	        if ( !Galaxy.user.id ) {
	            workflow_options.disabled = true; // disable workflows for anonymous users
	        }
	
	        var tab_workflow = new GalaxyMastheadTab( workflow_options );
	        this.masthead.append( tab_workflow );
	
	        //
	        // 'Shared Items' or Libraries tab.
	        //
	        var tab_shared = new GalaxyMastheadTab({
	            id              : 'shared',
	            title           : 'Shared Data',
	            content         : 'library/index',
	            title_attribute : 'Access published resources'
	        });
	
	        tab_shared.add({
	            title   : 'Data Libraries',
	            content : 'library/index'
	        });
	
	        tab_shared.add({
	            title   : 'Data Libraries Beta',
	            content : 'library/list',
	            divider : true
	        });
	
	        tab_shared.add({
	            title   : 'Published Histories',
	            content : 'history/list_published'
	        });
	
	        tab_shared.add({
	            title   : 'Published Workflows',
	            content : 'workflow/list_published'
	
	        });
	
	        tab_shared.add({
	            title   : 'Published Visualizations',
	            content : 'visualization/list_published'
	        });
	
	        tab_shared.add({
	            title   : 'Published Pages',
	            content : 'page/list_published'
	        });
	
	        this.masthead.append(tab_shared);
	
	        //
	        // Lab menu.
	        //
	        if ( this.options.user_requests ) {
	            var tab_lab = new GalaxyMastheadTab({
	                id      : 'lab',
	                title   : 'Lab'
	            });
	            tab_lab.add({
	                title   : 'Sequencing Requests',
	                content : 'requests/index'
	            });
	            tab_lab.add({
	                title   : 'Find Samples',
	                content : 'requests/find_samples_index'
	            });
	            tab_lab.add({
	                title   : 'Help',
	                content : this.options.lims_doc_url
	            });
	            this.masthead.append( tab_lab );
	        }
	
	        //
	        // Visualization tab.
	        //
	
	        var visualization_options = {
	            id              : 'visualization',
	            title           : 'Visualization',
	            content         : 'visualization/list',
	            title_attribute : 'Visualize datasets'
	        }
	
	        // disable visualizations for anonymous users
	        if ( !Galaxy.user.id ) {
	            visualization_options.disabled = true;
	        }
	        var tab_visualization = new GalaxyMastheadTab( visualization_options );
	
	        // add submenu only when user is logged in
	        if ( Galaxy.user.id ) {
	            tab_visualization.add({
	                title   : 'New Track Browser',
	                content : 'visualization/trackster',
	                target  : '_frame'
	            });
	            tab_visualization.add({
	                title   : 'Saved Visualizations',
	                content : 'visualization/list',
	                target  : '_frame'
	            });
	        }
	        this.masthead.append( tab_visualization );
	
	        //
	        // Admin.
	        //
	        if ( Galaxy.user.get( 'is_admin' ) ) {
	            var tab_admin = new GalaxyMastheadTab({
	                id              : 'admin',
	                title           : 'Admin',
	                content         : 'admin',
	                extra_class     : 'admin-only',
	                title_attribute : 'Administer this Galaxy'
	            });
	            this.masthead.append( tab_admin );
	        }
	
	        //
	        // Help tab.
	        //
	        var tab_help = new GalaxyMastheadTab({
	            id              : 'help',
	            title           : 'Help',
	            title_attribute : 'Support, contact, and community hubs'
	        });
	        if ( this.options.biostar_url ){
	            tab_help.add({
	                title   : 'Galaxy Biostar',
	                content : this.options.biostar_url_redirect,
	                target  : '_blank'
	            });
	            tab_help.add({
	                title   : 'Ask a question',
	                content : 'biostar/biostar_question_redirect',
	                target  : '_blank'
	            });
	        }
	        tab_help.add({
	            title   : 'Support',
	            content : this.options.support_url,
	            target  : '_blank'
	        });
	        tab_help.add({
	            title   : 'Search',
	            content : this.options.search_url,
	            target  : '_blank'
	        });
	        tab_help.add({
	            title   : 'Mailing Lists',
	            content : this.options.mailing_lists,
	            target  : '_blank'
	        });
	        tab_help.add({
	            title   : 'Videos',
	            content : this.options.screencasts_url,
	            target  : '_blank'
	        });
	        tab_help.add({
	            title   : 'Wiki',
	            content : this.options.wiki_url,
	            target  : '_blank'
	        });
	        tab_help.add({
	            title   : 'How to Cite Galaxy',
	            content : this.options.citation_url,
	            target  : '_blank'
	        });
	        if (this.options.terms_url){
	            tab_help.add({
	                title   : 'Terms and Conditions',
	                content : this.options.terms_url,
	                target  : '_blank'
	            });
	        }
	        this.masthead.append( tab_help );
	
	        //
	        // User tab.
	        //
	        if ( !Galaxy.user.id ){
	            var tab_user = new GalaxyMastheadTab({
	                id              : 'user',
	                title           : 'User',
	                extra_class     : 'loggedout-only',
	                title_attribute : 'Account registration or login'
	            });
	
	            // login
	            tab_user.add({
	                title   : 'Login',
	                content : 'user/login',
	                target  : 'galaxy_main'
	            });
	
	            // register
	            if ( this.options.allow_user_creation ){
	                tab_user.add({
	                    title   : 'Register',
	                    content : 'user/create',
	                    target  : 'galaxy_main'
	                });
	            }
	
	            // add to masthead
	            this.masthead.append( tab_user );
	        } else {
	            var tab_user = new GalaxyMastheadTab({
	                id              : 'user',
	                title           : 'User',
	                extra_class     : 'loggedin-only',
	                title_attribute : 'Account preferences and saved data'
	            });
	
	            // show user logged in info
	            tab_user.add({
	                title   : 'Logged in as ' + Galaxy.user.get( 'email' )
	            });
	
	            tab_user.add({
	                title   : 'Preferences',
	                content : 'user?cntrller=user',
	                target  : 'galaxy_main'
	            });
	
	            tab_user.add({
	                title   : 'Custom Builds',
	                content : 'user/dbkeys',
	                target  : 'galaxy_main'
	            });
	
	            tab_user.add({
	                title   : 'Logout',
	                content : 'user/logout',
	                target  : '_top',
	                divider : true
	            });
	
	            // default tabs
	            tab_user.add({
	                title   : 'Saved Histories',
	                content : 'history/list',
	                target  : 'galaxy_main'
	            });
	            tab_user.add({
	                title   : 'Saved Datasets',
	                content : 'dataset/list',
	                target  : 'galaxy_main'
	            });
	            tab_user.add({
	                title   : 'Saved Pages',
	                content : 'page/list',
	                target  : '_top'
	            });
	
	            tab_user.add({
	                title   : 'API Keys',
	                content : 'user/api_keys?cntrller=user',
	                target  : 'galaxy_main'
	            });
	
	            if ( this.options.use_remote_user ){
	                tab_user.add({
	                    title   : 'Public Name',
	                    content : 'user/edit_username?cntrller=user',
	                    target  : 'galaxy_main'
	                });
	            }
	
	            // add to masthead
	            this.masthead.append( tab_user );
	        }
	
	        // identify active tab
	        if ( this.options.active_view ) {
	            this.masthead.highlight( this.options.active_view );
	        }
	    }
	});
	
	/** Masthead tab **/
	var GalaxyMastheadTab = Backbone.View.extend({
	    // main options
	    options:{
	        id              : '',
	        title           : '',
	        target          : '_parent',
	        content         : '',
	        type            : 'url',
	        scratchbook     : false,
	        onunload        : null,
	        visible         : true,
	        disabled        : false,
	        title_attribute : ''
	    },
	
	    // location
	    location: 'navbar',
	
	    // optional sub menu
	    $menu: null,
	
	    // events
	    events:{
	        'click .head' : '_head'
	    },
	
	    // initialize
	    initialize: function ( options ){
	        // read in defaults
	        if ( options ){
	            this.options = _.defaults( options, this.options );
	        }
	
	        // update url
	        if ( this.options.content !== undefined && this.options.content.indexOf( '//' ) === -1 ){
	            this.options.content = Galaxy.root + this.options.content;
	        }
	
	        // add template for tab
	        this.setElement( $( this._template( this.options ) ) );
	
	        // disable menu items that are not available to anonymous user
	        // also show title to explain why they are disabled
	        if ( this.options.disabled ){
	            $( this.el ).find( '.root' ).addClass( 'disabled' );
	            this._attachPopover();
	        }
	
	        // visiblity
	        if ( !this.options.visible ){
	            this.hide();
	        }
	    },
	
	    // show
	    show: function(){
	        $(this.el).css({visibility : 'visible'});
	    },
	
	    // show
	    hide: function(){
	        $(this.el).css({visibility : 'hidden'});
	    },
	
	    // add menu item
	    add: function (options){
	        // menu option defaults
	        var menuOptions = {
	            title       : 'Title',
	            content     : '',
	            type        : 'url',
	            target      : '_parent',
	            scratchbook : false,
	            divider     : false
	        }
	
	        // read in defaults
	        if (options)
	            menuOptions = _.defaults(options, menuOptions);
	
	        // update url
	        if (menuOptions.content && menuOptions.content.indexOf('//') === -1)
	            menuOptions.content = Galaxy.root + menuOptions.content;
	
	        // check if submenu element is available
	        if (!this.$menu){
	            // insert submenu element into root
	            $(this.el).find('.root').append(this._templateMenu());
	
	            // show caret
	            $(this.el).find('.symbol').addClass('caret');
	
	            // update element link
	            this.$menu = $(this.el).find('.popup');
	        }
	
	        // create
	        var $item = $(this._templateMenuItem(menuOptions));
	
	        // append menu
	        this.$menu.append($item);
	
	        // add events
	        var self = this;
	        $item.on('click', function(e){
	            // prevent default
	            e.preventDefault();
	
	            // no modifications if new tab is requested
	            if (self.options.target === '_blank')
	                return true;
	
	            // load into frame
	            Galaxy.frame.add(options);
	        });
	
	        // append divider
	        if (menuOptions.divider)
	            this.$menu.append($(this._templateDivider()));
	    },
	
	    // show menu on header click
	    _head: function(e){
	        // prevent default
	        e.preventDefault();
	
	        if (this.options.disabled){
	            return // prevent link following if menu item is disabled
	        }
	
	        // check for menu options
	        if (!this.$menu) {
	            Galaxy.frame.add(this.options);
	        }
	    },
	
	    _attachPopover : function(){
	        var $popover_element = $(this.el).find('.head');
	        $popover_element.popover({
	            html: true,
	            content: 'Please <a href="' + Galaxy.root + 'user/login?use_panels=True">log in</a> or <a href="' + Galaxy.root + 'user/create?use_panels=True">register</a> to use this feature.',
	            placement: 'bottom'
	        }).on('shown.bs.popover', function() { // hooking on bootstrap event to automatically hide popovers after delay
	            setTimeout(function() {
	                $popover_element.popover('hide');
	            }, 5000);
	        });
	     },
	
	    // fill template header
	    _templateMenuItem: function (options){
	        return '<li><a href="' + options.content + '" target="' + options.target + '">' + options.title + '</a></li>';
	    },
	
	    // fill template header
	    _templateMenu: function (){
	        return '<ul class="popup dropdown-menu"></ul>';
	    },
	
	    _templateDivider: function(){
	        return '<li class="divider"></li>';
	    },
	
	    // fill template
	    _template: function (options){
	        // start template
	        var tmpl =  '<ul id="' + options.id + '" class="nav navbar-nav" border="0" cellspacing="0">' +
	                        '<li class="root dropdown" style="">' +
	                            '<a class="head dropdown-toggle" data-toggle="dropdown" target="' + options.target + '" href="' + options.content + '" title="' + options.title_attribute + '">' +
	                                options.title + '<b class="symbol"></b>' +
	                            '</a>' +
	                        '</li>' +
	                    '</ul>';
	
	        // return template
	        return tmpl;
	    }
	});
	
	// return
	return {
	    GalaxyMenu: GalaxyMenu,
	    GalaxyMastheadTab: GalaxyMastheadTab
	};
	
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(/*! libs/backbone */ 2), __webpack_require__(/*! underscore */ 1), __webpack_require__(/*! jquery */ 3)))

/***/ },

/***/ 123:
/*!**********************************************!*\
  !*** ./galaxy/scripts/layout/scratchbook.js ***!
  \**********************************************/
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(Backbone, $, _) {// dependencies
	!(__WEBPACK_AMD_DEFINE_ARRAY__ = [__webpack_require__(/*! mvc/ui/ui-frames */ 15)], __WEBPACK_AMD_DEFINE_RESULT__ = function(Frames) {
	
	/** Frame manager uses the ui-frames to create the scratch book masthead icon and functionality **/
	var GalaxyFrame = Backbone.View.extend({
	    // base element
	    el_main: 'body',
	
	    // frame active/disabled
	    active: false,
	
	    // button active
	    button_active: null,
	
	    // button load
	    button_load  : null,
	
	    // initialize
	    initialize : function(options) {
	        options = options || {};
	
	        // add to masthead menu
	        var self = this;
	
	        // create frames
	        this.frames = new Frames.View({
	            visible: false,
	        });
	
	        // add activate icon
	        this.button_active = new GalaxyMastheadIcon({
	            icon        : 'fa-th',
	            tooltip     : 'Enable/Disable Scratchbook',
	            onclick     : function() { self._activate(); },
	            onunload    : function() {
	                if (self.frames.length() > 0) {
	                    return "You opened " + self.frames.length() + " frame(s) which will be lost.";
	                }
	            }
	        });
	
	        // add load icon
	        this.button_load = new GalaxyMastheadIcon({
	            icon        : 'fa-eye',
	            tooltip     : 'Show/Hide Scratchbook',
	            onclick     : function(e) {
	                if (self.frames.visible) {
	                    self.frames.hide();
	                } else {
	                    self.frames.show();
	                }
	            },
	            with_number : true
	        });
	
	        // add to masthead
	        if( options.masthead ){
	            options.masthead.append(this.button_active);
	            options.masthead.append(this.button_load);
	        }
	
	        // create
	        this.setElement(this.frames.$el);
	
	        // append to main
	        $(this.el_main).append(this.$el);
	
	        // refresh menu
	        this.frames.setOnChange(function() {
	            self._refresh();
	        });
	        this._refresh();
	    },
	
	    /**
	     * Add a dataset to the frames.
	     */
	    add_dataset: function(dataset_id) {
	        var self = this;
	        __webpack_require__.e/* require */(1, function(__webpack_require__) { /* WEBPACK VAR INJECTION */(function($, _) {var __WEBPACK_AMD_REQUIRE_ARRAY__ = [__webpack_require__(/*! mvc/dataset/data */ 13)]; (function(DATA) {
	            var dataset = new DATA.Dataset({ id: dataset_id });
	            $.when( dataset.fetch() ).then( function() {
	                // Construct frame config based on dataset's type.
	                var frame_config = {
	                        title: dataset.get('name')
	                    },
	                    // HACK: For now, assume 'tabular' and 'interval' are the only
	                    // modules that contain tabular files. This needs to be replaced
	                    // will a is_datatype() function.
	                    is_tabular = _.find(['tabular', 'interval'], function(data_type) {
	                        return dataset.get('data_type').indexOf(data_type) !== -1;
	                    });
	
	                // Use tabular chunked display if dataset is tabular; otherwise load via URL.
	                if (is_tabular) {
	                    var tabular_dataset = new DATA.TabularDataset(dataset.toJSON());
	                    _.extend(frame_config, {
	                        type: 'other',
	                        content: function( parent_elt ) {
	                            DATA.createTabularDatasetChunkedView({
	                                model: tabular_dataset,
	                                parent_elt: parent_elt,
	                                embedded: true,
	                                height: '100%'
	                            });
	                        }
	                    });
	                }
	                else {
	                    _.extend(frame_config, {
	                        type: 'url',
	                        content: Galaxy.root + 'datasets/' +
	                                 dataset.id + '/display/?preview=True'
	                    });
	                }
	
	                self.add(frame_config);
	
	            });
	        }.apply(null, __WEBPACK_AMD_REQUIRE_ARRAY__));
	/* WEBPACK VAR INJECTION */}.call(this, __webpack_require__(/*! jquery */ 3), __webpack_require__(/*! underscore */ 1)))});
	
	    },
	
	    /**
	     * Add a trackster visualization to the frames.
	     */
	    add_trackster_viz: function(viz_id) {
	        var self = this;
	        __webpack_require__.e/* require */(2, function(__webpack_require__) { /* WEBPACK VAR INJECTION */(function($, _) {var __WEBPACK_AMD_REQUIRE_ARRAY__ = [__webpack_require__(/*! viz/visualization */ 124), __webpack_require__(/*! viz/trackster */ 126)]; (function(visualization, trackster) {
	            var viz = new visualization.Visualization({id: viz_id});
	            $.when( viz.fetch() ).then( function() {
	                var ui = new trackster.TracksterUI(Galaxy.root);
	
	                // Construct frame config based on dataset's type.
	                var frame_config = {
	                        title: viz.get('name'),
	                        type: 'other',
	                        content: function(parent_elt) {
	                            // Create view config.
	                            var view_config = {
	                                container: parent_elt,
	                                name: viz.get('title'),
	                                id: viz.id,
	                                // FIXME: this will not work with custom builds b/c the dbkey needed to be encoded.
	                                dbkey: viz.get('dbkey'),
	                                stand_alone: false
	                            },
	                            latest_revision = viz.get('latest_revision'),
	                            drawables = latest_revision.config.view.drawables;
	
	                            // Set up datasets in drawables.
	                            _.each(drawables, function(d) {
	                                d.dataset = {
	                                    hda_ldda: d.hda_ldda,
	                                    id: d.dataset_id
	                                };
	                            });
	
	                            view = ui.create_visualization(view_config,
	                                                           latest_revision.config.viewport,
	                                                           latest_revision.config.view.drawables,
	                                                           latest_revision.config.bookmarks,
	                                                           false);
	                        }
	                    };
	
	                self.add(frame_config);
	            });
	        }.apply(null, __WEBPACK_AMD_REQUIRE_ARRAY__));
	/* WEBPACK VAR INJECTION */}.call(this, __webpack_require__(/*! jquery */ 3), __webpack_require__(/*! underscore */ 1)))});
	    },
	
	    /**
	     * Add and display a new frame/window based on options.
	     */
	    add: function(options){
	        // open new tab
	        if (options.target == '_blank'){
	            window.open(options.content);
	            return;
	        }
	
	        // reload entire window
	        if (options.target == '_top' || options.target == '_parent' || options.target == '_self'){
	            window.location = options.content;
	            return;
	        }
	
	        // validate
	        if (!this.active){
	            // fix url if main frame is unavailable
	            var $galaxy_main = $(window.parent.document).find('#galaxy_main');
	            if (options.target == 'galaxy_main' || options.target == 'center'){
	                if ($galaxy_main.length === 0){
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
	
	        // add to frames view
	        this.frames.add(options);
	    },
	
	    // activate/disable panel
	    _activate: function (){
	        // check
	        if (this.active){
	            // disable
	            this.active = false;
	
	            // toggle
	            this.button_active.untoggle();
	
	            // hide panel
	            this.frames.hide();
	        } else {
	            // activate
	            this.active = true;
	
	            // untoggle
	            this.button_active.toggle();
	        }
	    },
	
	    // update frame counter
	    _refresh: function(){
	        // update on screen counter
	        this.button_load.number(this.frames.length());
	
	        // check
	        if(this.frames.length() === 0)
	            this.button_load.hide();
	        else
	            this.button_load.show();
	
	        // check
	        if (this.frames.visible) {
	            this.button_load.toggle();
	        } else {
	            this.button_load.untoggle();
	        }
	    }
	});
	
	/** Masthead icon **/
	var GalaxyMastheadIcon = Backbone.View.extend({
	    // icon options
	    options:{
	        id              : '',
	        icon            : 'fa-cog',
	        tooltip         : '',
	        with_number     : false,
	        onclick         : function() { alert ('clicked') },
	        onunload        : null,
	        visible         : true
	    },
	
	    // location identifier for masthead class
	    location: 'iconbar',
	
	    // initialize
	    initialize: function (options){
	        // read in defaults
	        if (options)
	            this.options = _.defaults(options, this.options);
	
	        // add template for icon
	        this.setElement($(this._template(this.options)));
	
	        // configure icon
	        var self = this;
	        $(this.el).find('.icon').tooltip({title: this.options.tooltip, placement: 'bottom'})
	                                .on('mouseup', self.options.onclick);
	
	        // visiblity
	        if (!this.options.visible)
	            this.hide();
	    },
	
	    // show
	    show: function(){
	        $(this.el).css({visibility : 'visible'});
	    },
	
	    // show
	    hide: function(){
	        $(this.el).css({visibility : 'hidden'});
	    },
	
	    // switch icon
	    icon: function (new_icon){
	        // update icon class
	        $(this.el).find('.icon').removeClass(this.options.icon)
	                                .addClass(new_icon);
	
	        // update icon
	        this.options.icon = new_icon;
	    },
	
	    // toggle
	    toggle: function(){
	        $(this.el).addClass('toggle');
	    },
	
	    // untoggle
	    untoggle: function(){
	        $(this.el).removeClass('toggle');
	    },
	
	    // set/get number
	    number: function(new_number){
	        $(this.el).find('.number').text(new_number);
	    },
	
	    // fill template icon
	    _template: function (options){
	        var tmpl =  '<div id="' + options.id + '" class="symbol">' +
	                        '<div class="icon fa fa-2x ' + options.icon + '"></div>';
	        if (options.with_number)
	            tmpl+=      '<div class="number"></div>';
	        tmpl +=     '</div>';
	
	        // return template
	        return tmpl;
	    }
	});
	
	// return
	return {
	    GalaxyFrame: GalaxyFrame,
	    GalaxyMastheadIcon: GalaxyMastheadIcon
	};
	
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(/*! libs/backbone */ 2), __webpack_require__(/*! jquery */ 3), __webpack_require__(/*! underscore */ 1)))

/***/ },

/***/ 140:
/*!****************************************************!*\
  !*** ./galaxy/scripts/mvc/user/user-quotameter.js ***!
  \****************************************************/
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(Backbone, _, $) {!(__WEBPACK_AMD_DEFINE_ARRAY__ = [
	    __webpack_require__(/*! mvc/base-mvc */ 6),
	    __webpack_require__(/*! utils/localization */ 8)
	], __WEBPACK_AMD_DEFINE_RESULT__ = function( baseMVC, _l ){
	
	var logNamespace = 'user';
	//==============================================================================
	/** @class View to display a user's disk/storage usage
	 *      either as a progress bar representing the percentage of a quota used
	 *      or a simple text element displaying the human readable size used.
	 *  @name UserQuotaMeter
	 *  @augments Backbone.View
	 */
	var UserQuotaMeter = Backbone.View.extend( baseMVC.LoggableMixin ).extend(
	/** @lends UserQuotaMeter.prototype */{
	    _logNamespace : logNamespace,
	
	    /** Defaults for optional settings passed to initialize */
	    options : {
	        warnAtPercent   : 85,
	        errorAtPercent  : 100
	    },
	
	    /** Set up, accept options, and bind events */
	    initialize : function( options ){
	        this.log( this + '.initialize:', options );
	        _.extend( this.options, options );
	
	        //this.bind( 'all', function( event, data ){ this.log( this + ' event:', event, data ); }, this );
	        this.model.bind( 'change:quota_percent change:total_disk_usage', this.render, this );
	    },
	
	    /** Re-load user model data from the api */
	    update : function( options ){
	        this.log( this + ' updating user data...', options );
	        this.model.loadFromApi( this.model.get( 'id' ), options );
	        return this;
	    },
	
	    /** Is the user over their quota (if there is one)?
	     * @returns {Boolean} true if over quota, false if no quota or under quota
	     */
	    isOverQuota : function(){
	        return ( this.model.get( 'quota_percent' ) !== null
	              && this.model.get( 'quota_percent' ) >= this.options.errorAtPercent );
	    },
	
	    /** Render the meter when they have an applicable quota. Will render as a progress bar
	     *      with their percentage of that quota in text over the bar.
	     *  @fires quota:over when user is over quota (>= this.errorAtPercent)
	     *  @fires quota:under when user is under quota
	     *  @fires quota:under:approaching when user is >= this.warnAtPercent of their quota
	     *  @fires quota:under:ok when user is below this.warnAtPercent
	     *  @returns {jQuery} the rendered meter
	     */
	    _render_quota : function(){
	        var modelJson = this.model.toJSON(),
	            //prevPercent = this.model.previous( 'quota_percent' ),
	            percent = modelJson.quota_percent,
	            //meter = $( UserQuotaMeter.templates.quota( modelJson ) );
	            $meter = $( this._templateQuotaMeter( modelJson ) ),
	            $bar = $meter.find( '.progress-bar' );
	        //this.log( this + '.rendering quota, percent:', percent, 'meter:', meter );
	
	        // OVER QUOTA: color the quota bar and show the quota error message
	        if( this.isOverQuota() ){
	            //this.log( '\t over quota' );
	            $bar.attr( 'class', 'progress-bar progress-bar-danger' );
	            $meter.find( '.quota-meter-text' ).css( 'color', 'white' );
	            //TODO: only trigger event if state has changed
	            this.trigger( 'quota:over', modelJson );
	
	        // APPROACHING QUOTA: color the quota bar
	        } else if( percent >= this.options.warnAtPercent ){
	            //this.log( '\t approaching quota' );
	            $bar.attr( 'class', 'progress-bar progress-bar-warning' );
	            //TODO: only trigger event if state has changed
	            this.trigger( 'quota:under quota:under:approaching', modelJson );
	
	        // otherwise, hide/don't use the msg box
	        } else {
	            $bar.attr( 'class', 'progress-bar progress-bar-success' );
	            //TODO: only trigger event if state has changed
	            this.trigger( 'quota:under quota:under:ok', modelJson );
	        }
	        return $meter;
	    },
	
	    /** Render the meter when the user has NO applicable quota. Will render as text
	     *      showing the human readable sum storage their data is using.
	     *  @returns {jQuery} the rendered text
	     */
	    _render_usage : function(){
	        //var usage = $( UserQuotaMeter.templates.usage( this.model.toJSON() ) );
	        var usage = $( this._templateUsage( this.model.toJSON() ) );
	        this.log( this + '.rendering usage:', usage );
	        return usage;
	    },
	
	    /** Render either the quota percentage meter or the human readable disk usage
	     *      depending on whether the user model has quota info (quota_percent === null -> no quota)
	     *  @returns {Object} this UserQuotaMeter
	     */
	    render : function(){
	        //this.log( this + '.rendering' );
	        var meterHtml = null;
	
	        // no quota on server ('quota_percent' === null (can be valid at 0)), show usage instead
	        this.log( this + '.model.quota_percent:', this.model.get( 'quota_percent' ) );
	        if( ( this.model.get( 'quota_percent' ) === null )
	        ||  ( this.model.get( 'quota_percent' ) === undefined ) ){
	            meterHtml = this._render_usage();
	
	        // otherwise, render percent of quota (and warning, error)
	        } else {
	            meterHtml = this._render_quota();
	            //TODO: add the original text for unregistered quotas
	            //tooltip = "Your disk quota is %s.  You can increase your quota by registering a Galaxy account."
	        }
	
	        this.$el.html( meterHtml );
	        this.$el.find( '.quota-meter-text' ).tooltip();
	        return this;
	    },
	
	    _templateQuotaMeter : function( data ){
	        return [
	            '<div id="quota-meter" class="quota-meter progress">',
	                '<div class="progress-bar" style="width: ', data.quota_percent, '%"></div>',
	                '<div class="quota-meter-text" style="top: 6px"',
	                    (( data.nice_total_disk_usage )?( ' title="Using ' + data.nice_total_disk_usage + '">' ):( '>' )),
	                    _l( 'Using' ), ' ', data.quota_percent, '%',
	                '</div>',
	            '</div>'
	        ].join( '' );
	    },
	
	    _templateUsage : function( data ){
	        return [
	            '<div id="quota-meter" class="quota-meter" style="background-color: transparent">',
	                '<div class="quota-meter-text" style="top: 6px; color: white">',
	                    (( data.nice_total_disk_usage )?( _l( 'Using ' ) + data.nice_total_disk_usage ):( '' )),
	                '</div>',
	            '</div>'
	        ].join( '' );
	    },
	
	    toString : function(){
	        return 'UserQuotaMeter(' + this.model + ')';
	    }
	});
	
	
	//==============================================================================
	return {
	    UserQuotaMeter : UserQuotaMeter
	};}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(/*! libs/backbone */ 2), __webpack_require__(/*! underscore */ 1), __webpack_require__(/*! jquery */ 3)))

/***/ }

});
//# sourceMappingURL=login.bundled.js.map