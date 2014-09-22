define([], function() {

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
        closing_callback : null
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
        } else{
            this.$body.css('max-height', $(window).height() / 2);
        }

        // fix width
        if (this.options.width){
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

});
