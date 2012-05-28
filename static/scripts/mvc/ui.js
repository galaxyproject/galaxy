/**
 * -- Functions for creating large UI elements. --
 */
 
/**
 * Returns an IconButtonMenuView for the provided configuration.
 * Configuration is a list of dictionaries where each dictionary
 * defines an icon button. Each dictionary must have the following
 * elements: icon_class, title, and on_click.
 */
var create_icon_buttons_menu = function(config) {
    // Create and initialize menu.
    var buttons = new IconButtonCollection( 
            _.map(config, function(button_config) { return new IconButton(button_config); })
        );
    
    return new IconButtonMenuView( {collection: buttons} );
};

/**
 * -- Utility models and views for Galaxy objects. --
 */
 
/**
 * Necessary Galaxy paths.
 */
var GalaxyPaths = Backbone.Model.extend({
    defaults: {
        root_path: "",
        image_path: ""
    }
});

/**
 * Clickable button represented as an icon.
 */
var IconButton = Backbone.Model.extend({
    defaults: {
        title: "",
        icon_class: "",
        on_click: null
    }
});

var IconButtonCollection = Backbone.Collection.extend({
    model: IconButton
});

/**
 * Menu with multiple icon buttons. Views are not needed nor used for individual buttons.
 */
var IconButtonMenuView = Backbone.View.extend({
    tagName: 'div',
    
    render: function() {
        var self = this;
        this.collection.each(function(button) {
            // Create and add icon button to menu.
            $("<a/>").attr('href', 'javascript:void(0)')
                     .attr('title', button.attributes.title)
                     .addClass('icon-button menu-button')
                     .addClass(button.attributes.icon_class)
                     .appendTo(self.$el)
                     .click(button.attributes.on_click);
        });
        return this;
    }
});

/**
 * 
 */
var Grid = Backbone.Collection.extend({
    
});

/**
 *
 */
var GridView = Backbone.View.extend({
    
});


