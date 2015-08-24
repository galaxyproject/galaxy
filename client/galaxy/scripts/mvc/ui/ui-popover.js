// dependencies
define(['utils/utils'], function(Utils) {

var View = Backbone.View.extend({

    // default options
    optionsDefault: {
        with_close  : true,
        container   : 'body',
        title       : null,
        placement   : 'top'
    },

    // visibility flag
    visible: false,

    // initialize
    initialize: function (options) {
        // link this
        var self = this;

        // update options
        this.options = _.defaults(options, this.optionsDefault);

        // set element
        this.setElement(this._template(this.options));

        // attach popover to parent
        this.options.container.parent().append(this.$el);

        // attach close
        if (this.options.with_close) {
            this.$el.find('#close').on('click', function() { self.hide(); });
        }

        // generate unique id
        this.uid = Utils.uid();

        // add event to hide if click is outside of popup
        var self = this;
        $('body').on('mousedown.' + this.uid,  function(e) { self._hide(e) });
    },

    // title
    title: function(val) {
        if (val !== undefined) {
            this.$el.find('.popover-title-label').html(val);
        }
    },

    // show
    show: function () {
        // show popover
        this.$el.show();
        this.visible = true;

        // calculate position
        var position = this._get_placement(this.options.placement);

        // set position
        this.$el.css(position);
    },

    // hide
    hide: function () {
        this.$el.hide();
        this.visible = false;
    },

    // append new doms to popover content
    append: function($el) {
        this.$el.find('.popover-content').append($el);
    },

    // empty popover content
    empty: function($el) {
        this.$el.find('.popover-content').empty();
    },

    // remove event handler and dom
    remove: function() {
        $('body').off('mousedown.' + this.uid);
        this.$el.remove();
    },

    // calculate position and error
    _get_placement: function(placement) {
        // get popover dimensions
        var width               = this._get_width(this.$el);
        var height              = this.$el.height();

        // get container details
        var $container = this.options.container;
        var container_width     = this._get_width($container);
        var container_height    = this._get_height($container);
        var container_position  = $container.position();

        // initialize position
        var top  = 0;
        var left = 0;

        // calculate position
        if (['top', 'bottom'].indexOf(placement) != -1) {
            left = container_position.left - width + (container_width + width) / 2;
            switch (placement) {
                case 'top':
                    top = container_position.top - height - 5;
                    break;
                case 'bottom':
                    top = container_position.top + container_height + 5;
                    break;
            }
        } else {
            top = container_position.top - height + (container_height + height) / 2;
            switch (placement) {
                case 'right':
                    left = container_position.left + container_width;
                    break;
            }
        }

        // return
        return {top: top, left: left};
    },

    // width
    _get_width: function($el) {
        return $el.width() + parseInt($el.css('padding-left')) + parseInt($el.css('padding-right'))
    },

    // height
    _get_height: function($el) {
        return $el.height() + parseInt($el.css('padding-top')) + parseInt($el.css('padding-bottom'))
    },

    // remove
    _hide : function(e) {
        // the 'is' for buttons that trigger popups
        // the 'has' for icons within a button that triggers a popup
        if (!$(this.options.container).is(e.target) &&
            !$(this.el).is(e.target) &&
            $(this.el).has(e.target).length === 0) {
                this.hide();
        }
    },

    // template
    _template: function(options) {
        var tmpl =  '<div class="ui-popover popover fade ' + options.placement + ' in">' +
                        '<div class="arrow"/>' +
                        '<div class="popover-title">' +
                            '<div class="popover-title-label">' +
                                options.title +
                            '</div>';
        if (options.with_close) {
            tmpl +=         '<div id="close" class="popover-close fa fa-times-circle"/>';
        }
        tmpl +=         '</div>' +
                        '<div class="popover-content"/>' +
                    '</div>';
        return tmpl;
    }
});

return {
    View: View
}

});