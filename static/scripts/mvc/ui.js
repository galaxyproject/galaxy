/**
 * -- Functions for creating large UI elements. --
 */
// =============================================================================
/**
 * -- Utility models and views for Galaxy objects. --
 */
 
/**
 * Clickable button represented as an icon.
 */
var IconButton = Backbone.Model.extend({
    defaults: {
        title: "",
        icon_class: "",
        on_click: null,
        tooltip_config: {},
        
        isMenuButton : true,
        id          : null,
        href        : null,
        target      : null,
        enabled     : true,
        visible     : true
    }
    
    //validate : function( attributes ){
        //TODO: validate href or on_click
        //TODO: validate icon_class
    //}
});


/**
 *  
 */
var IconButtonView = Backbone.View.extend({
    
    initialize  : function(){
        // better rendering this way (for me anyway)
        this.model.attributes.tooltip_config = { placement : 'bottom' };
        this.model.bind( 'change', this.render, this );
    },
    
    render : function(){
        //NOTE: not doing this hide will lead to disappearing buttons when they're both being hovered over & rendered
        this.$el.tooltip( 'hide' );
        
        // template in common-templates.html 
        var newElem = $( Handlebars.partials.iconButton( this.model.toJSON() ) );
        newElem.tooltip( this.model.get( 'tooltip_config' ) );
        
        this.$el.replaceWith( newElem );
        this.setElement( newElem );
        
        return this;
    },
    
    events      : {
        'click' : 'click'
    },
    
    click : function( event ){
        // if on_click pass to that function
        if( this.model.attributes.on_click ){
            this.model.attributes.on_click( event );
            return false;
        }
        // otherwise, bubble up (to href or whatever)
        return true;
    }
});
//TODO: bc h.templates is gen. loaded AFTER ui, Handlebars.partials.iconButton === undefined
IconButtonView.templates = {
    iconButton : Handlebars.partials.iconButton
};


var IconButtonCollection = Backbone.Collection.extend({
    model: IconButton
});

//------------------------------------------------------------------------------
/**
 * Menu with multiple icon buttons. Views are not needed nor used for individual buttons.
 */
var IconButtonMenuView = Backbone.View.extend({
    tagName: 'div',

    initialize: function() {
        this.render();
    },
    
    render: function() {
        var self = this;
        this.collection.each(function(button) {
            // Create and add icon button to menu.
            var elt = 
            $('<a/>').attr('href', 'javascript:void(0)')
                     .attr('title', button.attributes.title)
                     .addClass('icon-button menu-button')
                     .addClass(button.attributes.icon_class)
                     .appendTo(self.$el)
                     .click(button.attributes.on_click);

            if (button.attributes.tooltip_config) {
                elt.tooltip(button.attributes.tooltip_config);
            }
        });
        return this;
    }
});

/**
 * Returns an IconButtonMenuView for the provided configuration.
 * Configuration is a list of dictionaries where each dictionary
 * defines an icon button. Each dictionary must have the following
 * elements: icon_class, title, and on_click.
 */
var create_icon_buttons_menu = function(config, global_config) {
    if (!global_config) { global_config = {}; }

    // Create and initialize menu.
    var buttons = new IconButtonCollection( 
            _.map(config, function(button_config) { 
                return new IconButton(_.extend(button_config, global_config)); 
            })
        );
    
    return new IconButtonMenuView( {collection: buttons} );
};


// =============================================================================
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

// =============================================================================
/**
 * Necessary Galaxy paths.
 */
var GalaxyPaths = Backbone.Model.extend({
    defaults: {
        root_path: "",
        image_path: ""
    }
});














