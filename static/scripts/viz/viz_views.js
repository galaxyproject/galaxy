define( ["libs/underscore"], function(_) {

/**
 * View for track/group header.
 */
var TrackHeaderView = Backbone.View.extend({
    className: 'track-header',

    initialize: function() {
        // Watch and update name changes.
        this.model.config.get('name').on('change:value', this.update_name, this);
        this.render();
    },

    render: function() {
        this.$el.append($("<div/>").addClass(this.model.drag_handle_class));
        this.$el.append($("<div/>").addClass("track-name")
                                   .text(this.model.config.get_value('name')));

        // Icons container.
        this.action_icons = {};
        this.render_action_icons();

        // Suppress double clicks in header so that they do not impact viz under header.
        this.$el.dblclick( function(e) { e.stopPropagation(); } );
        
        // Needed for floating elts in header.
        this.$el.append( $("<div style='clear: both'/>") );
    },

    update_name: function() {
        this.$el.find('.track-name').text(this.model.config.get_value('name'));
    },

    render_action_icons: function() {
        var self = this;
        this.icons_div = $("<div/>").addClass('track-icons').hide().appendTo(this.$el);
        _.each(this.model.action_icons_def, function(icon_dict) {
            self.add_action_icon(icon_dict.name, icon_dict.title, icon_dict.css_class, 
                                 icon_dict.on_click_fn, icon_dict.prepend, icon_dict.hide);
        });

        // Set up behavior for modes popup.
        this.set_display_modes(this.model.display_modes);
    },

    /**
     * Add an action icon to this object. Appends icon unless prepend flag is specified.
     */
    add_action_icon: function(name, title, css_class, on_click_fn, prepend, hide) {
        var self = this;
        this.action_icons[name] = $("<a/>").attr("title", title)
                                           .addClass("icon-button").addClass(css_class).tooltip()
                                           .click( function() { on_click_fn(self.model); } )
                                           .appendTo(this.icons_div);
        if (hide) {
            this.action_icons[name].hide();
        }
    },

    /**
     * Set track's modes and update mode icon popup.
     */
    set_display_modes: function(new_modes, init_mode) {
        if (!new_modes) { return; }

        // HACK: move this out of view and into track.

        // Set modes, init mode.
        this.model.display_modes = new_modes;
        this.model.mode = (init_mode || this.model.config.get_value('mode') || this.model.display_modes[0]);
        
        this.action_icons.mode_icon.attr("title", "Set display mode (now: " + this.mode + ")");

        // Setup popup menu for changing modes.
        var self = this,
            track = this.model,
            mode_mapping = {};
        for (var i = 0, len = track.display_modes.length; i < len; i++) {
            var mode = track.display_modes[i];
            mode_mapping[mode] = function(mode) {
                return function() { 
                    track.change_mode(mode);
                    // HACK: the popup menu messes with the track's hover event, so manually show/hide
                    // icons div for now.
                    //self.icons_div.show(); 
                    //track.container_div.mouseleave(function() { track.icons_div.hide(); } ); 
                };
            }(mode);
        }

        make_popupmenu(this.action_icons.mode_icon, mode_mapping);
    }
});

return {
    TrackHeaderView: TrackHeaderView
};

});